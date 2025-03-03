import { Component, OnDestroy, OnInit } from '@angular/core';
import { TextareaModule } from 'primeng/textarea';
import { ButtonModule } from 'primeng/button';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';
import { Message } from '../../interfaces/message';
import { Subscription } from 'rxjs';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [CommonModule, TextareaModule, ButtonModule, FormsModule],
  templateUrl: './chat-input.component.html',
  styleUrl: './chat-input.component.css',
})
export class ChatInputComponent implements OnInit, OnDestroy {
  message: string = '';
  isLoading: boolean = false;
  isTokenLimited: boolean = false;
  currentChatId: string | null = null;
  isBackendInitializing: boolean = true;

  subscriptions: Subscription[] = [];

  constructor(private chatService: ChatService) {}

  ngOnDestroy(): void {
    this.subscriptions.forEach((subscription) => subscription.unsubscribe());
  }

  ngOnInit(): void {
    // Subscribe to loading state
    const loadingSubscription = this.chatService.loading$.subscribe(
      (loading) => (this.isLoading = loading)
    );

    // Subscribe to current chat changes
    const chatSubscription = this.chatService.currentChatId$.subscribe(
      (chatId) => {
        if (chatId) {
          this.currentChatId = chatId;
          // Check if this chat is token limited
          this.isTokenLimited = this.chatService.isChatTokenLimited(chatId);
        }
      }
    );

    // Subscribe to token limit reached events
    const tokenLimitSubscription =
      this.chatService.tokenLimitReached$.subscribe((chatId) => {
        if (chatId === this.currentChatId) {
          this.isTokenLimited = true;
        }
      });

    const backendStatusSubscription =
      this.chatService.backendInitializing$.subscribe((initializing) => {
        this.isBackendInitializing = initializing;
      });

    this.subscriptions.push(
      loadingSubscription,
      chatSubscription,
      tokenLimitSubscription,
      backendStatusSubscription
    );
  }

  sendMessage() {
    if (this.message.trim() && !this.isLoading && !this.isTokenLimited && !this.isBackendInitializing) {
      const currentChatId = this.chatService.getCurrentChatId();

      if (!currentChatId) {
        console.error('No active chat to send message to');
        return;
      }

      const newMessage: Message = {
        content: this.message,
        id: Date.now().toString(),
        type: 'Human',
      };

      // Use the new chat-specific method instead of the old session-based method
      this.chatService.sendMessageToChat(currentChatId, newMessage);
      this.message = '';
    }
  }

  onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey && !this.isTokenLimited && !this.isBackendInitializing && !this.isLoading) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
