import Editor from "@monaco-editor/react";
import { Upload, PlayCircle, Loader2 } from "lucide-react";
import { useRef } from "react";

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
  isAnalyzing: boolean;
  disabled?: boolean;
}

export default function CodeEditor({ code, onChange, onAnalyze, isAnalyzing, disabled }: CodeEditorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onChange(String(reader.result ?? ""));
    reader.readAsText(file);
    e.target.value = "";
  }

  return (
    <div className="flex flex-col h-full rounded-lg border border-bg-border overflow-hidden bg-bg-panel">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-bg-border bg-bg-elevated">
        <div className="flex items-center gap-2 text-sm text-gray-300">
          <span className="mono">program.cpp</span>
        </div>
        <div className="flex items-center gap-2">
          <input ref={fileInputRef} type="file" accept=".cpp,.cc,.cxx" className="hidden" onChange={handleFileUpload} />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border border-bg-border text-gray-300 hover:bg-bg-elevated hover:text-white transition"
          >
            <Upload size={13} /> Upload .cpp
          </button>
          <button
            onClick={onAnalyze}
            disabled={disabled || isAnalyzing}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md bg-accent text-black hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <PlayCircle size={14} />}
            {isAnalyzing ? "Analyzing..." : "Analyze"}
          </button>
        </div>
      </div>
      <div className="flex-1 min-h-[320px]">
        <Editor
          height="100%"
          defaultLanguage="cpp"
          language="cpp"
          theme="vs-dark"
          value={code}
          onChange={(v) => onChange(v ?? "")}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontFamily: "JetBrains Mono, Fira Code, monospace",
            padding: { top: 12 },
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}
