import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { ButtonModule } from 'primeng/button';
import { FormsModule } from '@angular/forms';
import { ChatInputComponent } from '../chat-input/chat-input.component';
import { ChatWindowComponent } from '../chat-window/chat-window.component';
import { ChatService } from '../../services/chat.service';

@Component({
  selector: 'app-chat',
  imports: [
    InputTextModule,
    ButtonModule,
    MessageModule,
    FormsModule,
    ChatInputComponent,
    ChatWindowComponent
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css'
})
export class ChatComponent implements OnChanges {
  @Input() currentChatId: string | null = null;

  constructor(private chatService: ChatService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['currentChatId'] && changes['currentChatId'].currentValue) {
      // Update the current chat in the service
      this.chatService.setCurrentChat(changes['currentChatId'].currentValue);
    }
  }
}
