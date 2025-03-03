import {
  AfterViewChecked,
  Component,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { ScrollPanel, ScrollPanelModule } from 'primeng/scrollpanel';
import { MessageModule } from 'primeng/message';
import { PanelModule } from 'primeng/panel';
import { Message, MessageGroup } from '../../interfaces/message';
import { Subscription } from 'rxjs';
import { ChatService } from '../../services/chat.service';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { MarkdownModule } from 'ngx-markdown';
import { ButtonModule } from 'primeng/button';
import { ChartModule } from 'primeng/chart';

@Component({
  selector: 'app-chat-window',
  imports: [
    ScrollPanelModule,
    MessageModule,
    PanelModule,
    ProgressSpinnerModule,
    MarkdownModule,
    ButtonModule,
    ChartModule
  ],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.css',
})
export class ChatWindowComponent
  implements OnInit, OnDestroy, AfterViewChecked
{
  @ViewChild('scrollPanel') private scrollPanel!: ScrollPanel;
  messages: Message[] = [];
  isLoading: boolean = false;
  private shouldScroll: boolean = true;
  chartOptions: any;
  messageGroups: MessageGroup[] = [];
  animateMessageIds: Set<string> = new Set();

  private subscriptions: Subscription[] = [];
  private currentChatId: string | null = null;
  isBackendInitializing: boolean = true;

  constructor(private chatService: ChatService) {
    this.initChartOptions();
  }

  shouldAnimateMessage(message: Message): boolean {
    console.log("Checking animation for message:", message.id, this.animateMessageIds.has(message.id || ""));
    // Asegurarnos de que no falle si el ID es undefined
    return message.id ? this.animateMessageIds.has(message.id) : false;
  }

  private initChartOptions() {
    this.chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#ffffff',
          },
        },
        title: {
          display: true,
          text: 'Evolución del Precio',
          color: '#ffffff',
        },
      },
      scales: {
        x: {
          ticks: {
            color: '#ffffff',
          },
          grid: {
            color: 'rgba(255,255,255,0.2)',
          },
        },
        y: {
          ticks: {
            color: '#ffffff',
            callback: (value: number) => `${value.toFixed(2)}€`,
          },
          grid: {
            color: 'rgba(255,255,255,0.2)',
          },
        },
      },
    };
  }

  async ngOnInit() {
    // Listen for chat changes
    const chatSubscription = this.chatService.currentChatId$.subscribe(
      (chatId) => {
        if (chatId && chatId !== this.currentChatId) {
          this.loadChat(chatId);
        }
      }
    );

    // Subscribe to new messages for the current chat
    const messagesSubscription = this.chatService.messages$.subscribe(
      (message) => {
        if (message.content !== '') {
          // Add message to appropriate group
          if (message.type === 'Human') {
            this.messageGroups.push({ humanMessage: message });
            // Activar el auto-scroll para mensajes humanos también
            this.shouldScroll = true;
          } else if (message.type === 'AI') {
            const lastGroup = this.messageGroups[this.messageGroups.length - 1];
            if (lastGroup) {
              lastGroup.aiMessage = message;

              // Marcar este mensaje para animación
              if (message.id) {
                console.log("Marking message for animation:", message.id);
                this.animateMessageIds.add(message.id);

                // Después de un tiempo, quitar la animación para no repetirla en scroll
                setTimeout(() => {
                  this.animateMessageIds.delete(message.id || "");
                }, 10000); // 10 segundos es tiempo suficiente para la animación
              } else {
                console.log("Message has no ID:", message);
              }
            }
            this.shouldScroll = true;
          }
        }
      }
    );

    const loadingSubscription = this.chatService.loading$.subscribe(
      (loading) => {
        this.isLoading = loading;
        // Si se completa la carga, activar el scroll
        if (!loading) {
          this.shouldScroll = true;
        }
      }
    );

    const toolResultSubscription = this.chatService.toolResults$.subscribe(
      (message) => {
        if (message.type === 'tool_result' && message.content && this.isGraphableContent(message.content)) {
          const lastGroup = this.messageGroups[this.messageGroups.length - 1];
          if (lastGroup) {
            // Inicializar arrays si no existen
            if (!lastGroup.toolResults) {
              lastGroup.toolResults = [];
            }
            if (!lastGroup.chartData) {
              lastGroup.chartData = [];
            }

            // Añadir el nuevo resultado
            lastGroup.toolResults.push(message);

            // Procesar datos del gráfico
            const chartData = this.createChartData(message.content);
            if (chartData) {
              lastGroup.chartData.push(chartData);
            }

            this.shouldScroll = true;
          }
        }
      }
    );

    const backendStatusSubscription = this.chatService.backendInitializing$.subscribe(
      (initializing) => {
        this.isBackendInitializing = initializing;
      }
    );

    this.subscriptions.push(
      messagesSubscription,
      loadingSubscription,
      toolResultSubscription,
      chatSubscription,
      backendStatusSubscription
    );
  }

  async loadChat(chatId: string) {
    this.isLoading = true;
    this.currentChatId = chatId;
    this.messageGroups = [];

    // Limpiar el conjunto de IDs de mensajes a animar
    // Esto es importante para que los mensajes cargados de un chat existente
    // no se animen como si fueran nuevos
    console.log("Clearing animation messages set");
    this.animateMessageIds.clear();

    try {
      // Load messages for this specific chat ID
      console.log(`Loading chat ${chatId}`);
      const messages = await this.chatService.loadChat(chatId);
      console.log(`Loaded ${messages.length} messages for chat ${chatId}:`, messages);

      if (messages.length > 0) {
        // Organizamos los mensajes en grupos pero NO los marcamos para animar
        this.messageGroups = this.groupMessages(messages);
        console.log(`Created ${this.messageGroups.length} message groups`);

        this.shouldScroll = true;
      }
    } catch (error) {
      console.error('Error loading chat:', error);
    } finally {
      this.isLoading = false;
    }
  }

  private isPriceData(data: any): boolean {
    // Verificar si tenemos la estructura correcta con graph_data
    if (!data || !data.graph_data) {
      return false;
    }

    // Verificar el formato de los datos dentro de graph_data
    return Object.entries(data.graph_data).every(([key, value]) => {
      // Convertir fecha de DD-MM-YYYY a YYYY-MM-DD para Date.parse
      const [day, month, year] = key.split('-');
      const isoDate = `${year}-${month}-${day}`;

      const dateValid = !isNaN(Date.parse(isoDate));
      const valueValid = typeof value === 'number';

      return dateValid && valueValid;
    });
  }

  private isGraphableContent(content: string): boolean {
    // Si es vacío, definitivamente no es un gráfico
    if (!content || content.trim() === '') {
      return false;
    }

    // Verificar que comienza como JSON
    if (!content.trim().startsWith('{')) {
      return false;
    }

    try {
      const parsed = JSON.parse(content);
      // Verificar si tiene la estructura esperada para un gráfico
      return this.isPriceData(parsed);
    } catch (e) {
      // No es JSON válido
      return false;
    }
  }

  private createChartData(content: string): any {

    try {
      const toolResult = JSON.parse(content);

      if (!this.isPriceData(toolResult)) {
        return null;
      }

      const priceData = toolResult.graph_data;

      // Convertir fechas a formato Date para ordenar correctamente
      const sortedDates = Object.keys(priceData).sort((a, b) => {
        const [dayA, monthA, yearA] = a.split('-');
        const [dayB, monthB, yearB] = b.split('-');
        return (
          new Date(`${yearA}-${monthA}-${dayA}`).getTime() -
          new Date(`${yearB}-${monthB}-${dayB}`).getTime()
        );
      });

      return {
        labels: sortedDates.map((date) => {
          const [day, month, year] = date.split('-');
          return `${day}/${month}/${year.slice(-2)}`;
        }),
        datasets: [
          {
            label: 'Precio Estimado (€)',
            data: sortedDates.map((date) => priceData[date]),
            fill: false,
            borderColor: '#8c62ff',
            tension: 0.4,
            pointBackgroundColor: '#713dff',
          },
        ],
      };
    } catch (error) {
      console.error('Error creating chart data:', error);
      return null;
    }
  }

  private groupMessages(messages: Message[]): MessageGroup[] {
    console.log("Original messages:", JSON.parse(JSON.stringify(messages)));
    const groups: MessageGroup[] = [];

    // Primero, filtrar mensajes no graficables
    const filteredMessages = messages.filter(m =>
      m.type === 'Human' ||
      m.type === 'AI' && m.content != '' ||
      ((m.type === 'tool' || m.type === 'tool_result') && this.isGraphableContent(m.content))
    );

    // Recorrer los mensajes y detectar patrones Human → [tool_results] → AI para reordenarlos
    const reorderedMessages: Message[] = [];
    let i = 0;

    // Manejo especial para mensaje inicial de bienvenida
    if (filteredMessages.length > 0 && filteredMessages[0].type === 'AI') {
      reorderedMessages.push(filteredMessages[0]);
      i = 1;
    }

    while (i < filteredMessages.length) {
      const currentMessage = filteredMessages[i];

      // Caso 1: Tenemos un mensaje Human
      if (currentMessage.type === 'Human') {
        // Añadir el mensaje Human
        reorderedMessages.push(currentMessage);
        i++;

        // Buscar un patrón "tool_results seguidos por AI" después de este Human
        const toolResults: Message[] = [];
        let aiMessage: Message | null = null;
        let j = i;

        // Recolectar tool_results y buscar un AI
        while (j < filteredMessages.length &&
               filteredMessages[j].type !== 'Human') {

          if (filteredMessages[j].type === 'AI') {
            aiMessage = filteredMessages[j];
            j++; // Incluir este mensaje en el avance
            break; // Salir del bucle inner cuando encontramos un AI
          } else if (filteredMessages[j].type === 'tool' ||
                    filteredMessages[j].type === 'tool_result') {
            toolResults.push(filteredMessages[j]);
          }
          j++;
        }

        // Si encontramos un AI, añadirlo primero, luego los tool_results
        if (aiMessage) {
          reorderedMessages.push(aiMessage);
          reorderedMessages.push(...toolResults);
        } else {
          // No hay AI, solo añadir los tool_results en su orden original
          reorderedMessages.push(...toolResults);
        }

        // Avanzar el índice principal al último mensaje procesado
        i = j;
      }
      // Caso 2: Otro tipo de mensaje (AI o tool_result solitarios)
      else {
        reorderedMessages.push(currentMessage);
        i++;
      }
    }

    console.log("Reordered messages:", JSON.parse(JSON.stringify(reorderedMessages)));

    // Agrupar los mensajes reordenados
    let currentGroup: MessageGroup = {};

    for (const message of reorderedMessages) {
      switch (message.type) {
        case 'Human':
          if (currentGroup.humanMessage || currentGroup.aiMessage) {
            groups.push(currentGroup);
            currentGroup = {};
          }
          currentGroup.humanMessage = message;
          break;

        case 'AI':
          if (currentGroup.aiMessage) {
            groups.push(currentGroup);
            currentGroup = {};
          }
          currentGroup.aiMessage = message;
          break;

        case 'tool':
        case 'tool_result':
          if (currentGroup.aiMessage) {
            // Inicializar arrays si no existen
            if (!currentGroup.toolResults) {
              currentGroup.toolResults = [];
            }
            if (!currentGroup.chartData) {
              currentGroup.chartData = [];
            }

            currentGroup.toolResults.push(message);
            const chartData = this.createChartData(message.content);
            if (chartData) {
              currentGroup.chartData.push(chartData);
            }
          } else {
            // Caso especial: herramienta sin AI previo
            const chartData = this.createChartData(message.content);
            groups.push({
              toolResults: [message],
              chartData: chartData ? [chartData] : []
            });
          }
          break;
      }
    }

    // No olvidar el último grupo
    if (currentGroup.humanMessage || currentGroup.aiMessage) {
      groups.push(currentGroup);
    }

    console.log("Final groups:", JSON.parse(JSON.stringify(groups)));
    return groups;
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private scrollToBottom() {
    if (this.scrollPanel && this.scrollPanel.contentViewChild) {
      // Asegurarse de que el panel esté actualizado
      this.scrollPanel.refresh();

      // Usar setTimeout con tiempo para dar tiempo al DOM a actualizar completamente
      setTimeout(() => {
        const element = this.scrollPanel?.contentViewChild?.nativeElement;
        if (element) {
          // Primero intentar con comportamiento suave
          element.scrollTo({
            top: element.scrollHeight,
            behavior: 'smooth',
          });


        }
      }, 50);
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach((subscription) => subscription.unsubscribe());
  }
}


