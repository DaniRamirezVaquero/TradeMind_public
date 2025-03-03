import { Component, OnDestroy, OnInit } from '@angular/core';
import { ChatComponent } from './components/chat/chat.component';
import { HeaderComponent } from './components/header/header.component';
import { CommonModule } from '@angular/common';
import { ChatListComponent } from './components/chat-list/chat-list.component';
import { ChatSession } from './interfaces/chat-session';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';
import { DialogModule } from 'primeng/dialog';
import { FormsModule } from '@angular/forms';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { ChatService } from './services/chat.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    ChatComponent,
    HeaderComponent,
    ChatListComponent,
    ConfirmDialogModule,
    ToastModule,
    DialogModule,
    FormsModule,
    InputTextModule,
    ButtonModule,
  ],
  providers: [ConfirmationService, MessageService],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit, OnDestroy {
  isDrawerOpen = false;
  currentChatId: string | null = null;
  chats: ChatSession[] = [];
  subscriptions: Subscription[] = [];

  // Variables para el diálogo de edición de título
  displayTitleEditDialog: boolean = false;
  editingChatId: string | null = null;
  editedChatTitle: string = '';

  constructor(
    private confirmationService: ConfirmationService,
    private messageService: MessageService,
    private chatService: ChatService
  ) {}

  async ngOnInit() {
    const backendReadySubscription = this.chatService.backendReady$.subscribe(
      (ready) => {
        if (ready) {
          // Inicializar la aplicación una vez que el backend esté listo
          this.initializeApp();
        }
      }
    );

    const chatTitleSubscription = this.chatService.chatTitleUpdate$.subscribe(
      ({ chatId, title }) => {
        const chat = this.chats.find((c) => c.id === chatId);
        if (chat) {
          // Solo animar si el título cambió de "Nueva conversación" a otro
          const isNewToCustom =
            chat.title === 'Nueva conversación' &&
            title !== 'Nueva conversación';

          // Actualizar el título
          chat.title = title;

          // Notificar al componente de lista que anime este título
          if (isNewToCustom) {
            const event = new CustomEvent('animateTitle', {
              detail: { chatId },
            });
            window.dispatchEvent(event);
          }
        }
      }
    );

    const tokenLimitSubscription =
      this.chatService.tokenLimitReached$.subscribe((chatId) => {
        // Buscar el chat que ha alcanzado el límite
        const chat = this.chats.find((c) => c.id === chatId);

        if (chat) {
          // Mostrar notificación
          this.messageService.add({
            severity: 'warn',
            summary: 'Límite alcanzado',
            detail: `La conversación "${chat.title}" ha alcanzado el límite máximo de tokens. Por favor, crea una nueva conversación para continuar.`,
            sticky: true,
          });

          // Actualizar la información del chat para mostrar indicador de límite
          chat.tokenLimitReached = true;
        }
      });

    this.subscriptions.push(chatTitleSubscription, tokenLimitSubscription, backendReadySubscription);
  }

  /// Método para inicializar la aplicación cuando el backend está listo
private async initializeApp() {
  try {
    console.log('Inicializando aplicación con backend activo');

    // Inicializar sesión y cargar chats
    const sessionResponse = await this.chatService.initializeSession();

    // Convertir fechas de strings a objetos Date
    this.chats = sessionResponse.chats.map((chat) => ({
      ...chat,
      createdAt: new Date(chat.createdAt),
    }));

    // Seleccionar el primer chat si está disponible
    if (this.chats.length > 0) {
      this.selectChat(this.chats[0].id);
    } else {
      // Si no hay chats, crear uno nuevo
      await this.createNewChat();
    }

    console.log('Aplicación inicializada correctamente');
  } catch (error) {
    console.error('Error initializing app:', error);
    this.messageService.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al inicializar la aplicación. Por favor, recarga la página.',
      sticky: true
    });
  }
}

  toggleDrawer() {
    this.isDrawerOpen = !this.isDrawerOpen;
  }

  // Método para abrir el diálogo de edición
  openTitleEditDialog(data: { id: string; title: string }): void {
    this.editingChatId = data.id;
    this.editedChatTitle = data.title;
    this.displayTitleEditDialog = true;
  }

  // Confirmar el cambio de título
  confirmTitleEdit(): void {
    if (this.editingChatId && this.editedChatTitle?.trim()) {
      this.renameChat({
        id: this.editingChatId,
        title: this.editedChatTitle.trim(),
      });
      this.cancelTitleEdit();
    }
  }

  // Cancelar la edición
  cancelTitleEdit(): void {
    this.displayTitleEditDialog = false;
    this.editingChatId = null;
    this.editedChatTitle = '';
  }

  selectChat(chatId: string) {
    // Update App component state
    this.editingChatId = null;
    this.currentChatId = chatId;

    // Update ChatService state
    this.chatService.setCurrentChat(chatId);

    // In mobile, close drawer when selecting a chat
    if (window.innerWidth < 768) {
      this.isDrawerOpen = false;
    }
  }

  async createNewChat() {
    try {
      const newChat = await this.chatService.createNewChat(
        'Nueva conversación'
      );

      // Convert date and add to chats array
      const formattedChat = {
        ...newChat,
        createdAt: new Date(newChat.createdAt),
      };

      this.chats.unshift(formattedChat);
      this.selectChat(formattedChat.id);
    } catch (error) {
      console.error('Error creating new chat:', error);
      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo crear una nueva conversación',
      });
    }
  }

  // Modificar deleteChat
  async deleteChat(chatId: string): Promise<void> {
    this.confirmationService.confirm({
      message: '¿Estás seguro de que deseas eliminar esta conversación?',
      header: 'Confirmar eliminación',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Sí, eliminar',
      rejectLabel: 'Cancelar',
      acceptButtonStyleClass: 'p-button-danger',
      accept: async () => {
        try {
          await this.chatService.deleteChat(chatId);

          // Remove from local array
          const index = this.chats.findIndex((chat) => chat.id === chatId);
          if (index !== -1) {
            this.chats.splice(index, 1);
          }

          // If we deleted the active chat, select another one
          if (this.currentChatId === chatId) {
            if (this.chats.length > 0) {
              this.selectChat(this.chats[0].id);
            } else {
              // If no chats left, create a new one
              await this.createNewChat();
            }
          }

          this.messageService.add({
            severity: 'success',
            summary: 'Eliminado',
            detail: 'La conversación ha sido eliminada correctamente',
          });
        } catch (error) {
          console.error('Error deleting chat:', error);
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No se pudo eliminar la conversación',
          });
        }
      },
    });
  }

  // Modificar el método renameChat
  async renameChat(data: { id: string; title: string }): Promise<void> {
    // If no title, open dialog
    if (!data.title) {
      // Find chat to get its current title
      const chat = this.chats.find((chat) => chat.id === data.id);
      if (chat) {
        this.openTitleEditDialog({ id: data.id, title: chat.title });
      }
      return;
    }

    // If title is empty, show error
    if (data.title.trim() === '') {
      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: 'El título no puede estar vacío',
      });
      return;
    }

    try {
      // Update title using service
      const updatedChat = await this.chatService.updateChatTitle(
        data.id,
        data.title.trim()
      );

      // Update local chat
      const chat = this.chats.find((chat) => chat.id === data.id);
      if (chat) {
        chat.title = updatedChat.title;
      }

      this.messageService.add({
        severity: 'success',
        summary: 'Actualizado',
        detail: 'El título ha sido actualizado correctamente',
      });
    } catch (error) {
      console.error('Error updating chat title:', error);
      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo actualizar el título',
      });
    }
  }

  // Método para actualizar previewText de un chat
  updateChatPreview(chatId: string, previewText: string): void {
    const chat = this.chats.find((chat) => chat.id === chatId);
    if (chat) {
      chat.previewText = previewText;
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach((s) => s.unsubscribe());
  }
}
