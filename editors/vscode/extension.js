// ishvacerto VS Code extension.
//
// Runs the local `ishvacerto --json <file>` CLI on the current Python file and turns its three-valued
// verdict into editor feedback:
//   VERIFIED -> clear diagnostics + info message
//   REFUTED  -> an Error diagnostic carrying the exact counterexample
//   ABSTAIN  -> a subtle info message, NO error (an honest non-answer is not a failure)
//
// The pure JSON->verdict parser is exported as parseVerdict() and does NOT require('vscode'), so it can be
// unit-tested headlessly (see test/parse.test.js). vscode is required lazily inside activate()/runtime fns.

'use strict';

/**
 * Pure parser: turn the CLI's `--json` stdout into a normalized verdict object.
 * No vscode dependency -> headless-testable.
 *
 * @param {string} stdout - raw stdout from `ishvacerto --json <file>` (one JSON object).
 * @returns {{verdict:string, entry_point:string, spec_source:string, counterexample:string, detail:object}}
 * @throws {Error} if stdout is not parseable JSON or lacks a verdict field.
 */
function parseVerdict(stdout) {
  if (stdout == null) throw new Error('ishvacerto: empty output');
  // The CLI prints exactly one JSON object; be tolerant of trailing whitespace/newlines and any
  // leading noise by locating the first '{' .. last '}'.
  const text = String(stdout);
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start === -1 || end === -1 || end < start) {
    throw new Error('ishvacerto: no JSON object in output: ' + text.slice(0, 200));
  }
  const obj = JSON.parse(text.slice(start, end + 1));
  if (typeof obj.verdict !== 'string') {
    throw new Error('ishvacerto: JSON missing "verdict" field');
  }
  return {
    verdict: obj.verdict,
    entry_point: obj.entry_point || '',
    spec_source: obj.spec_source || '',
    counterexample: obj.counterexample || '',
    detail: obj.detail || {},
  };
}

// ---------------------------------------------------------------------------------------------------------
// Everything below requires vscode and is only reached when the extension is actually activated by VS Code.
// ---------------------------------------------------------------------------------------------------------

let _diagnostics = null;

function activate(context) {
  const vscode = require('vscode');
  const { execFile } = require('child_process');

  _diagnostics = vscode.languages.createDiagnosticCollection('ishvacerto');
  context.subscriptions.push(_diagnostics);

  function configuredPath() {
    return vscode.workspace.getConfiguration('ishvacerto').get('path', 'ishvacerto');
  }

  function verifyDocument(document) {
    if (!document || document.languageId !== 'python' || document.isUntitled) {
      return;
    }
    const filePath = document.fileName;
    const exe = configuredPath();

    // exe may be a bare command ("ishvacerto") or include args (e.g. "python -m ishvacerto").
    const parts = exe.split(/\s+/).filter(Boolean);
    const cmd = parts[0];
    const args = parts.slice(1).concat(['--json', filePath]);

    // exit code 1 (REFUTED) is expected and not a spawn error -> we still parse stdout.
    execFile(cmd, args, { timeout: 30000 }, (err, stdout, stderr) => {
      if (err && (err.code === 'ENOENT' || /ENOENT/.test(String(err.message)))) {
        vscode.window.showErrorMessage(
          'ishvacerto: command "' + cmd + '" not found. Install it with `pip install ishvacerto`, ' +
          'or set the "ishvacerto.path" setting (e.g. "python -m ishvacerto").'
        );
        return;
      }

      let verdict;
      try {
        verdict = parseVerdict(stdout);
      } catch (e) {
        const detail = (stderr && String(stderr).trim()) || (err && String(err.message)) || String(e.message);
        vscode.window.showErrorMessage('ishvacerto: could not read verifier output. ' + detail);
        return;
      }

      applyVerdict(vscode, document, verdict);
    });
  }

  function verifyActive() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showInformationMessage('ishvacerto: no active editor.');
      return;
    }
    verifyDocument(editor.document);
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('ishvacerto.verifyFile', verifyActive)
  );

  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((document) => {
      const onSave = vscode.workspace.getConfiguration('ishvacerto').get('verifyOnSave', false);
      if (onSave) {
        verifyDocument(document);
      }
    })
  );
}

/** Map a parsed verdict onto diagnostics + user messages. Separated so activate() stays readable. */
function applyVerdict(vscode, document, verdict) {
  const uri = document.uri;
  const fn = verdict.entry_point || '(unknown)';

  if (verdict.verdict === 'REFUTED') {
    let msg = 'ishvacerto REFUTED ' + fn;
    if (verdict.counterexample) {
      msg += ' — counterexample: ' + verdict.counterexample;
    }
    if (verdict.detail && verdict.detail.got !== undefined && verdict.detail.expected !== undefined) {
      msg += ' (got ' + verdict.detail.got + ', expected ' + verdict.detail.expected + ')';
    }
    const range = new vscode.Range(0, 0, 0, Math.max(1, (document.lineAt(0).text || '').length));
    const diag = new vscode.Diagnostic(range, msg, vscode.DiagnosticSeverity.Error);
    diag.source = 'ishvacerto';
    _diagnostics.set(uri, [diag]);
    vscode.window.showErrorMessage(msg);
  } else if (verdict.verdict === 'VERIFIED') {
    _diagnostics.delete(uri);
    const src = verdict.spec_source ? ' [' + verdict.spec_source + ']' : '';
    vscode.window.showInformationMessage('ishvacerto VERIFIED ' + fn + src);
  } else {
    // ABSTAIN (or any non-REFUTED verdict): an honest non-answer is NOT an error.
    _diagnostics.delete(uri);
    vscode.window.setStatusBarMessage('ishvacerto: ABSTAIN ' + fn + ' (no checkable spec)', 4000);
  }
}

function deactivate() {
  if (_diagnostics) {
    _diagnostics.clear();
    _diagnostics.dispose();
    _diagnostics = null;
  }
}

module.exports = { activate, deactivate, parseVerdict };
