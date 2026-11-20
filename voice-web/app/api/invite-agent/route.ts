import { NextRequest, NextResponse } from 'next/server';
import {
  AgoraClient,
  Agent,
  Area,
  AresSTT,
  DeepgramSTT,
  ExpiresIn,
  MiniMaxTTS,
  MurfTTS,
  OpenAI,
  SarvamSTT,
} from 'agora-agents';
import { ClientStartRequest, AgentResponse } from '@/types/conversation';
import { DEFAULT_AGENT_UID } from '@/lib/agora';
import { BACKEND, backendHeaders } from '@/lib/suno/backend';

// System prompt that defines the agent's personality and behavior.
// Swap this out to change what the agent talks about.
const ADA_PROMPT = `You are **Ada**, an agentic developer advocate from **Agora**. You help developers understand and build with Agora's Conversational AI platform.

# What Agora Actually Is
Agora is a real-time communications company. The product you represent is the **Agora Conversational AI Engine** — it lets developers add voice AI agents to any app by connecting ASR, LLM, and TTS into a real-time pipeline over Agora's SD-RTN (Software Defined Real-Time Network). Key facts:
- The product is called the **Conversational AI Engine** (not "Chorus", not "Harmony", or any other name you might invent)
- It runs a full ASR → LLM → TTS pipeline with sub-500ms latency
- It supports Deepgram, Microsoft, and others for ASR; OpenAI, Anthropic, and others for LLM; ElevenLabs, Microsoft, and others for TTS
- Agora's SD-RTN is its global real-time network infrastructure — not "SDRTN"
- MCP in this context means **Model Context Protocol** (Anthropic's open standard for connecting AI models to tools/data), not "multi-channel processing"
- Agora does not have a product called Chorus, Harmony, or any similar name — do not invent product names

# Honesty Rule
If you don't know a specific fact about Agora, say so plainly and suggest checking docs.agora.io. Never invent product names, feature names, or capabilities.

# Persona & Tone
- Friendly, technically credible, concise. You're a peer who builds things, not a support agent.
- Plain English. No marketing fluff.

# Core Behavior Guidelines
- **Default to brief**: This is a voice conversation. Keep most replies to 1–2 sentences. Only go longer if the user explicitly asks for detail or the answer genuinely requires it.
- **Never list or enumerate**: No bullet points, no numbered steps. Say the single most important thing.
- **Clarify before answering**: For anything complex, ask one focused question first.
- **Ask at most one question per turn**: Never stack questions.
- **Guide, don't lecture**: Unlock the next step, not everything at once.`;

// First thing the agent says when a user joins the channel.
const GREETING = `Hi there! I'm Ada, your virtual assistant from Agora. How can I help?`;

// agentUid identifies the AI in the RTC channel and shares its default with the client.
const agentUid = String(DEFAULT_AGENT_UID);

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

// TTS: Murf Falcon (BYOK) when NEXT_MURF_API_KEY is set — required for the
// Build with Agora hackathon. Falls back to Agora-managed MiniMax otherwise.
// Murf params per https://docs.agora.io/en/ai/models/tts/murf
const MURF_LOCALE: Record<string, string> = { en: 'en-IN', hi: 'hi-IN', ml: 'ml-IN', kn: 'kn-IN', ta: 'ta-IN' };

// Listening (speech recognition) per language.
//   en, hi : Deepgram nova-3 (Agora-managed, tested)
//   kn, ta : Agora ARES (managed, no extra key; its language list includes kn-IN and ta-IN)
//   ml     : Agora's own recognizers have no Malayalam, so Sarvam is used when NEXT_SARVAM_API_KEY is set;
//            otherwise the agent still SPEAKS Malayalam but listens with the English recognizer (poor).
const ARES_LANGUAGE: Record<string, 'kn-IN' | 'ta-IN'> = { kn: 'kn-IN', ta: 'ta-IN' };

function buildStt(lang: string) {
  if (lang === 'kn' || lang === 'ta') return new AresSTT();
  if (lang === 'ml' && process.env.NEXT_SARVAM_API_KEY) {
    return new SarvamSTT({ apiKey: process.env.NEXT_SARVAM_API_KEY, language: 'ml-IN' });
  }
  return new DeepgramSTT({ model: 'nova-3', language: lang === 'hi' ? 'hi' : 'en' });
}

function buildTts(lang: string = 'en') {
  const murfKey = process.env.NEXT_MURF_API_KEY;
  if (murfKey) {
    return new MurfTTS({
      key: murfKey,
      model: 'FALCON', // Murf accepts FALCON and routes it to Falcon 2.1
      voiceId: process.env.NEXT_MURF_VOICE_ID || 'hi-IN-jaya', // speaks en-IN, hi, ml, kn, ta
      locale: MURF_LOCALE[lang] ?? process.env.NEXT_MURF_LOCALE ?? 'en-IN',
      sampleRate: 24000,
    });
  }
  return new MiniMaxTTS({
    model: 'speech_2_6_turbo',
    voiceId: 'English_captivating_female1',
  });
}

// LLM: when NEXT_SUNOSAFE_LLM_URL and NEXT_SUNOSAFE_LLM_KEY are set, Agora
// Conversational AI sends each user turn to SunoSafe's own OpenAI-compatible
// endpoint (custom LLM). That endpoint runs the security tools and returns the
// words to speak. Agora forwards the key as "Authorization: Bearer <key>".
// Without those settings the Agora-managed default model is used.
const SUNOSAFE_GREETING =
  'Namaste, I am SunoSafe. You can ask me to check a message or a link.';

function sunoSafeLlmConfigured(): boolean {
  return Boolean(process.env.NEXT_SUNOSAFE_LLM_URL && process.env.NEXT_SUNOSAFE_LLM_KEY);
}

type Lang = 'en' | 'hi' | 'ml' | 'kn' | 'ta';
const LANGS: Lang[] = ['en', 'hi', 'ml', 'kn', 'ta'];


type VoicePlan = { incident?: number; mode: 'guard' | 'drill' | 'shield'; lang: Lang; greeting: string };

/** Validate the optional context and fetch the opening sentence from the private backend. */
async function planVoice(body: ClientStartRequest): Promise<VoicePlan> {
  const lang: Lang = LANGS.includes(body.lang as Lang) ? (body.lang as Lang) : 'en';
  const mode = body.mode === 'drill' || body.mode === 'shield' ? body.mode : 'guard';
  const incident = Number.isInteger(body.incident_id) && (body.incident_id ?? 0) > 0 ? body.incident_id : undefined;
  let greeting = lang === 'hi' ? 'नमस्ते, मैं सुनोसेफ़ हूँ। आप मुझसे किसी संदेश, लिंक या कॉल के बारे में पूछ सकते हैं।' : SUNOSAFE_GREETING;
  try {
    const path = mode === 'drill' ? `/api/voice/drill-greeting?lang=${lang}`
      : mode === 'shield' ? `/api/voice/shield-greeting?lang=${lang}`
      : !incident ? `/api/voice/greeting?lang=${lang}`
      : incident ? `/api/incidents/${incident}/voice-brief?lang=${lang}` : null;
    if (path) {
      const r = await fetch(BACKEND + path, { cache: 'no-store', headers: backendHeaders(), signal: AbortSignal.timeout(8000) });
      if (r.ok) greeting = ((await r.json()) as { greeting: string }).greeting.slice(0, 600);
    }
  } catch {
    /* keep the plain greeting: the agent can still investigate on request */
  }
  return { incident, mode, lang, greeting };
}

function buildLlm(channelName: string, plan: VoicePlan) {
  if (sunoSafeLlmConfigured()) {
    // One SunoSafe session per call, so approvals and case notes never mix between calls.
    const session = channelName.replace(/[^A-Za-z0-9_.-]/g, '_').slice(0, 64);
    const query = new URLSearchParams({ session, mode: plan.mode, lang: plan.lang });
    if (plan.incident) query.set('incident', String(plan.incident));
    return new OpenAI({
      apiKey: requireEnv('NEXT_SUNOSAFE_LLM_KEY'),
      url: `${requireEnv('NEXT_SUNOSAFE_LLM_URL')}?${query.toString()}`,
      model: 'sunosafe-agent',
      greetingMessage: plan.greeting,
      failureMessage: 'Sorry, I could not check that. Please try again.',
      maxHistory: 15,
    });
  }
  return new OpenAI({
    model: 'gpt-4o-mini',
    greetingMessage: GREETING,
    failureMessage: 'Please wait a moment.',
    maxHistory: 15,
    params: {
      max_tokens: 1024,
      temperature: 0.7,
      top_p: 0.95,
    },
  });
}

export async function POST(request: NextRequest) {
  try {
    // --- 1. Parse request ---

    const body: ClientStartRequest = await request.json();
    const { requester_id, channel_name } = body;
    const plan = await planVoice(body);

    // Validate required env vars on first request so misconfiguration surfaces
    // with a clear error message rather than a silent failure.
    const appId = requireEnv('NEXT_PUBLIC_AGORA_APP_ID');
    const appCertificate = requireEnv('NEXT_AGORA_APP_CERTIFICATE');

    if (!channel_name || !requester_id) {
      return NextResponse.json(
        { error: 'channel_name and requester_id are required' },
        { status: 400 },
      );
    }

    // --- 2. Build and start the agent ---

    // AgoraClient authenticates API calls to the Agora Conversational AI service.
    // area: change to Area.EU or Area.AP for European or Asia-Pacific deployments.
    const client = new AgoraClient({
      area: Area.US,
      appId,
      appCertificate,
    });

    // Pipeline: Deepgram (reseller) STT → OpenAI (reseller) LLM → MiniMax (reseller) TTS.
    // Omit vendor API keys for supported models — AgentKit infers reseller presets on start (see Agora Console / billing).
    const agent = new Agent({
      client,
      // With the SunoSafe LLM, the real instructions live in the SunoSafe backend
      // (it ignores system messages sent from here, so they cannot be tampered with).
      instructions: sunoSafeLlmConfigured() ? 'You are SunoSafe.' : ADA_PROMPT,
      greeting: sunoSafeLlmConfigured() ? plan.greeting : GREETING,
      failureMessage: 'Please wait a moment.',
      maxHistory: 50,
      // VAD controls how the agent detects the start and end of a user's turn.
      turnDetection: {
        ...(ARES_LANGUAGE[plan.lang] ? { language: ARES_LANGUAGE[plan.lang] } : {}),
        config: {
          speech_threshold: 0.5,
          start_of_speech: {
            mode: 'vad',
            vad_config: {
              interrupt_duration_ms: 160, // ms of speech before interruption triggers
              prefix_padding_ms: 300, // audio captured before speech is detected
            },
          },
          end_of_speech: {
            mode: 'vad',
            vad_config: {
              silence_duration_ms: 480, // ms of silence before turn ends
            },
          },
        },
      },
      // RTM is required for transcript events in the browser client.
      // enable_tools is required for MCP tool invocation.
      advancedFeatures: { enable_rtm: true, enable_tools: true },
      // Required for browser RTM events:
      // - data_channel: 'rtm' enables RTM delivery path for state/metrics/errors
      // - enable_error_message emits AGENT_ERROR payloads
      // - enable_metrics emits AGENT_METRICS latency payloads
      parameters: {
        // web client → ultra-low-latency chorus profile
        audio_scenario: 'chorus',
        data_channel: 'rtm',
        enable_error_message: true,
        enable_metrics: true,
      },
    })
      .withStt(
        buildStt(plan.lang),
        // BYOK: uncomment the following block and set NEXT_DEEPGRAM_API_KEY
        // new DeepgramSTT({
        //   apiKey: requireEnv('NEXT_DEEPGRAM_API_KEY'),
        //   model: 'nova-3',
        //   language: 'en',
        // }),
      )
      .withLlm(
        buildLlm(channel_name, plan),
        // BYOK: uncomment the following block and set NEXT_LLM_API_KEY and NEXT_LLM_URL
        // new OpenAI({
        //   apiKey: requireEnv('NEXT_LLM_API_KEY'),
        //   url: requireEnv('NEXT_LLM_URL'),
        //   model: 'gpt-4o-mini',
        //   greetingMessage: GREETING,
        //   failureMessage: 'Please wait a moment.',
        //   maxHistory: 15,
        //   maxTokens: 1024,
        //   temperature: 0.7,
        //   topP: 0.95,
        // }),
      )
      .withTts(
        buildTts(plan.lang),
        // BYOK — ElevenLabs (set NEXT_ELEVENLABS_API_KEY; optional NEXT_ELEVENLABS_VOICE_ID)
        // new (await import('agora-agents')).ElevenLabsTTS({
        //   key: requireEnv('NEXT_ELEVENLABS_API_KEY'),
        //   modelId: 'eleven_flash_v2_5',
        //   voiceId: process.env.NEXT_ELEVENLABS_VOICE_ID ?? 'pNInz6obpgDQGcFmaJgB',
        //   sampleRate: 24000,
        // }),
      );

    // remoteUids restricts the agent to only process audio from this user
    const session = agent.createSession({
      channel: channel_name,
      agentUid,
      remoteUids: [requester_id],
      idleTimeout: 30,
      expiresIn: ExpiresIn.hours(1),
      debug: false, // enable debug to show restful API calls in the console
    });

    const agentId = await session.start();

    return NextResponse.json({
      agent_id: agentId,
      create_ts: Math.floor(Date.now() / 1000),
      state: 'RUNNING',
    } as AgentResponse);
  } catch (error) {
    console.error('Error starting conversation:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Failed to start conversation',
      },
      { status: 500 },
    );
  }
}
