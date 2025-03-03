export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  previewText?: string;
  tokenLimitReached?: boolean;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
}
