import { Plus, Trash2 } from "lucide-react";
import type { TestCase } from "../types";

interface TestCaseEditorProps {
  testCases: TestCase[];
  onChange: (testCases: TestCase[]) => void;
}

export default function TestCaseEditor({ testCases, onChange }: TestCaseEditorProps) {
  function addTestCase() {
    onChange([...testCases, { name: `test_${testCases.length + 1}`, stdin: "" }]);
  }

  function updateTestCase(idx: number, patch: Partial<TestCase>) {
    const next = [...testCases];
    next[idx] = { ...next[idx], ...patch };
    onChange(next);
  }

  function removeTestCase(idx: number) {
    onChange(testCases.filter((_, i) => i !== idx));
  }

  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-wider text-gray-500">Test Cases</div>
        <button
          onClick={addTestCase}
          className="flex items-center gap-1 text-xs px-2 py-1 rounded-md border border-bg-border text-gray-300 hover:bg-bg-elevated"
        >
          <Plus size={13} /> Add
        </button>
      </div>

      {testCases.length === 0 && (
        <p className="text-xs text-gray-500">
          No test cases configured — analysis will run with empty stdin. Add a test case to supply program input.
        </p>
      )}

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {testCases.map((tc, idx) => (
          <div key={idx} className="flex items-start gap-2 bg-bg-elevated rounded-md p-2 border border-bg-border">
            <div className="flex-1 space-y-1.5">
              <input
                value={tc.name}
                onChange={(e) => updateTestCase(idx, { name: e.target.value })}
                className="w-full bg-transparent text-xs font-medium text-gray-200 border-b border-transparent focus:border-bg-border outline-none"
                placeholder="Test name"
              />
              <textarea
                value={tc.stdin}
                onChange={(e) => updateTestCase(idx, { stdin: e.target.value })}
                placeholder="stdin (optional)"
                rows={2}
                className="w-full bg-bg text-xs mono text-gray-300 rounded p-1.5 border border-bg-border outline-none resize-y"
              />
            </div>
            <button onClick={() => removeTestCase(idx)} className="text-gray-500 hover:text-accent-red mt-1">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
