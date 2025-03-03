import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ToggleSwitchModule } from 'primeng/toggleswitch';

@Component({
  selector: 'app-dark-mode-toggle',
  imports: [
    ToggleSwitchModule,
    CommonModule,
    FormsModule
  ],
  templateUrl: './dark-mode-toggle.component.html',
  styleUrl: './dark-mode-toggle.component.css'
})
export class DarkModeToggleComponent {

  checked: boolean = true;

  ngOnInit() {
    this.toggleDarkMode();
  }

  toggleDarkMode() {
    const element = document.querySelector('html');
    if (this.checked) {
      element?.classList.add('dark-mode');
    } else {
      element?.classList.remove('dark-mode');
    }
  }
}
