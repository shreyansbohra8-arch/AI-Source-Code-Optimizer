import { Cpu, Github, Activity } from "lucide-react";

interface SidebarProps {
  llmConfigured: boolean;
  compilerAvailable: boolean;
  compilerName: string;
}

export default function Sidebar({ llmConfigured, compilerAvailable, compilerName }: SidebarProps) {
  return (
    <aside className="hidden md:flex md:w-60 lg:w-64 flex-col border-r border-bg-border bg-bg-panel shrink-0">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-bg-border">
        <div className="w-8 h-8 rounded-md bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
          <Cpu size={18} className="text-white" />
        </div>
        <div>
          <div className="font-semibold text-sm leading-tight">CodeOpt AI</div>
          <div className="text-[11px] text-gray-500 leading-tight">C++ Optimization Agent</div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 text-sm">
        <div className="px-2 pb-2 text-[11px] uppercase tracking-wider text-gray-500">Workspace</div>
        <div className="flex items-center gap-2 px-2 py-2 rounded-md bg-bg-elevated text-gray-100">
          <Activity size={15} /> Analysis Console
        </div>
      </nav>

      <div className="px-4 py-4 border-t border-bg-border space-y-2 text-xs text-gray-400">
        <div className="flex items-center justify-between">
          <span>Compiler ({compilerName})</span>
          <span className={compilerAvailable ? "text-accent" : "text-accent-red"}>
            {compilerAvailable ? "● ready" : "● missing"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>LLM Agent</span>
          <span className={llmConfigured ? "text-accent" : "text-accent-yellow"}>
            {llmConfigured ? "● configured" : "● no API key"}
          </span>
        </div>
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 pt-2 text-gray-500 hover:text-gray-300"
        >
          <Github size={13} /> BCSE306 Mini Project
        </a>
      </div>
    </aside>
  );
}
