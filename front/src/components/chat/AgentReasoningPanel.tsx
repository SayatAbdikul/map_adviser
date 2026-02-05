import React, { useMemo, useState } from 'react';
import { Sparkles, ChevronDown, ChevronUp, GitBranch } from 'lucide-react';
import { useRouteStore } from '@/store/useRouteStore';
import type { ReasoningStep, RouteResponse } from '@/types';
import { isCoreAgentResponse } from '@/types';

const gradientBg =
  'bg-gradient-to-r from-[rgba(79,70,229,0.08)] via-[rgba(59,130,246,0.08)] to-[rgba(34,197,94,0.08)]';

const getSteps = (routeResponse: RouteResponse | null): ReasoningStep[] => {
  if (!routeResponse) return [];
  if (isCoreAgentResponse(routeResponse)) {
    return routeResponse.reasoning ?? [];
  }
  return (routeResponse as any)?.reasoning ?? [];
};

export const AgentReasoningPanel: React.FC = () => {
  const { routeResponse } = useRouteStore();
  const steps = useMemo(() => getSteps(routeResponse), [routeResponse]);
  const [open, setOpen] = useState(true);

  if (!steps.length) return null;

  return (
    <div className="px-3 pt-3">
      <div
        className={`rounded-2xl border app-border ${gradientBg} app-shadow-soft overflow-hidden`}
      >
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="w-full flex items-center justify-between px-3 py-2 text-left"
        >
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-white/70 shadow-sm">
              <Sparkles size={16} className="text-indigo-600" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-[color:var(--app-muted)]">LLM reasoning</p>
              <p className="text-sm font-semibold text-[color:var(--app-text)]">How the plan was built</p>
            </div>
          </div>
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>

        {open && (
          <div className="px-3 pb-3 space-y-2">
            {steps.map((step) => (
              <div
                key={step.id}
                className="rounded-xl border border-white/60 bg-white/70 backdrop-blur px-3 py-2 shadow-sm"
              >
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 rounded-full bg-[color:var(--app-accent-soft)] text-[color:var(--app-accent-strong)] flex items-center justify-center text-xs font-semibold">
                    {step.id}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1 text-sm font-semibold text-[color:var(--app-text)]">
                      {step.tool && <GitBranch size={14} className="text-[color:var(--app-muted)]" />}
                      <span className="truncate">{step.title}</span>
                    </div>
                    {step.input && (
                      <p className="text-xs text-[color:var(--app-muted)] mt-1 overflow-hidden break-words max-h-10">
                        {step.input}
                      </p>
                    )}
                    {step.output && (
                      <p className="text-xs text-[color:var(--app-text)] mt-1 overflow-hidden break-words max-h-16">
                        {step.output}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
