import Editor from "@monaco-editor/react";

interface CodeComparisonProps {
  original: string;
  optimized: string | null;
}

export default function CodeComparison({ original, optimized }: CodeComparisonProps) {
  return (
    <div className="rounded-lg border border-bg-border bg-bg-panel overflow-hidden">
      <div className="text-xs uppercase tracking-wider text-gray-500 px-4 pt-4 pb-2">
        Original vs Optimized
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-bg-border">
        <div className="bg-bg-panel">
          <div className="px-3 py-1.5 text-[11px] font-medium text-gray-400 border-b border-bg-border bg-bg-elevated">ORIGINAL CODE</div>
          <Editor
            height="360px"
            defaultLanguage="cpp"
            theme="vs-dark"
            value={original}
            options={{ readOnly: true, fontSize: 12, minimap: { enabled: false }, scrollBeyondLastLine: false }}
          />
        </div>
        <div className="bg-bg-panel">
          <div className="px-3 py-1.5 text-[11px] font-medium text-gray-400 border-b border-bg-border bg-bg-elevated">OPTIMIZED CANDIDATE</div>
          <Editor
            height="360px"
            defaultLanguage="cpp"
            theme="vs-dark"
            value={optimized ?? "// No optimized candidate was produced."}
            options={{ readOnly: true, fontSize: 12, minimap: { enabled: false }, scrollBeyondLastLine: false }}
          />
        </div>
      </div>
    </div>
  );
}
