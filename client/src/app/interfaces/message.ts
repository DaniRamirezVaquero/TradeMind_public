export interface FunctionCall {
  name: string;
  arguments: string;
}

export interface Message {
  content: string;
  type: 'AI' | 'Human' | 'tool_result' | 'tool' ;
  id?: string;
  additional_kwargs?: {
    function_call?: FunctionCall;
  };
}

export interface MessageGroup {
  humanMessage?: Message;
  aiMessage?: Message;
  // Cambiamos de un único tool result a un array
  toolResults?: Message[];
  // Cambiamos a un array de datos de gráficos
  chartData?: any[];
}
