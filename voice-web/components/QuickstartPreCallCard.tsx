'use client';

import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

type QuickstartPreCallCardProps = {
  isLoading: boolean;
  error: string | null;
  onStartConversation: () => void;
  context?: { incident_id?: number; mode?: 'guard' | 'drill' | 'shield'; lang?: string };
};

export function QuickstartPreCallCard({
  isLoading,
  error,
  onStartConversation,
  context = {},
}: QuickstartPreCallCardProps) {
  const heading = context.mode === 'shield'
    ? 'Call shield test'
    : context.mode === 'drill'
    ? 'Scam call practice'
    : context.incident_id ? 'SunoSafe has a warning for you' : 'Talk to SunoSafe';
  const sub = context.mode === 'shield'
    ? 'You play the caller. SunoSafe answers as it would a forwarded call, screens what you say, and warns the phone if it sounds like a scam. Use only made-up details.'
    : context.mode === 'drill'
    ? 'SunoSafe will pretend to be a scam caller so you can practise saying no. Never say real details.'
    : context.incident_id
      ? 'Tap to hear what SunoSafe found, ask why, and decide what to do.'
      : 'Ask about a message, a link or a call that worries you. Powered by Agora Conversational AI and Murf Falcon.';
  return (
    <div
      className="mx-auto flex w-[min(92vw,26.25rem)] animate-fade-up flex-col items-center rounded-[20px] border border-[#2b2b2b] px-10 py-10 text-center shadow-[0_10px_24px_rgba(0,0,0,0.28)]"
      style={{
        backgroundImage:
          'linear-gradient(164.988deg, rgba(54,54,54,0.2) 1.0596%, rgba(0,0,0,0) 96.089%), linear-gradient(90deg, rgb(16,16,16) 0%, rgb(16,16,16) 100%)',
      }}
    >
      <h1 className="text-[28px] font-medium leading-[1.2] text-white">
        {heading}
      </h1>
      <p className="mt-[14px] text-sm font-medium leading-6 text-muted-foreground">
        {sub}
      </p>

      <Button
        onClick={onStartConversation}
        disabled={isLoading}
        className="mt-10 h-14 w-full text-base rounded-lg border border-primary bg-primary text-sm font-medium text-black hover:border-white hover:bg-white hover:text-black disabled:hover:border-primary disabled:hover:bg-primary disabled:hover:text-black"
        aria-label={
          isLoading
            ? 'Starting conversation with AI agent'
            : 'Start conversation with AI agent'
        }
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Starting...
          </>
        ) : (
          'Start talking'
        )}
      </Button>
      {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
    </div>
  );
}
