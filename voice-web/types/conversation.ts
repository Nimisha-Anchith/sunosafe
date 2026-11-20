import type { RTMClient } from 'agora-rtm';

export interface AgoraTokenData {
  token: string;
  uid: string;
  channel: string;
  agentId?: string;
}

export interface ClientStartRequest {
  requester_id: string;
  channel_name: string;
  /** SunoSafe: incident the user opened the voice agent from (gives it context). */
  incident_id?: number;
  /** SunoSafe: 'guard' (normal) or 'drill' (scam practice). */
  mode?: 'guard' | 'drill';
  /** SunoSafe: preferred language for replies and voice. */
  lang?: 'en' | 'hi' | 'ml' | 'kn' | 'ta';
}

export type VoiceContext = Pick<ClientStartRequest, 'incident_id' | 'mode' | 'lang'>;

export interface StopConversationRequest {
  agent_id: string;
}

export interface AgentResponse {
  agent_id: string;
  create_ts: number;
  state: string;
}

export interface AgoraRenewalTokens {
  rtcToken: string;
  rtmToken: string;
}

export interface ConversationComponentProps {
  agoraData: AgoraTokenData;
  rtmClient: RTMClient;
  onTokenWillExpire: (uid: string) => Promise<AgoraRenewalTokens>;
  onEndConversation: () => void;
}
