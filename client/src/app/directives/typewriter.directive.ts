import { Directive, ElementRef, Input, OnInit, OnChanges, SimpleChanges, OnDestroy } from '@angular/core';

@Directive({
  selector: '[appTypewriter]',
  standalone: true
})
export class TypewriterDirective implements OnInit, OnChanges, OnDestroy {
  @Input() appTypewriter: string | undefined;
  @Input() typeSpeed: number = 70;
  @Input() startDelay: number = 200;

  private animationInProgress: boolean = false;
  private originalContent: string = '';
  private intervalId: number | null = null; // Store interval ID instead of using dataset

  constructor(private el: ElementRef<HTMLElement>) {}

  ngOnInit() {
    if (this.appTypewriter) {
      this.setupTypewriter(this.appTypewriter);
    } else {
      this.originalContent = this.el.nativeElement.textContent || '';
      this.setupTypewriter(this.originalContent);
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['appTypewriter'] && !changes['appTypewriter'].firstChange) {
      this.setupTypewriter(this.appTypewriter || '');
    }
  }

  ngOnDestroy() {
    this.stopAnimation();
  }

  private setupTypewriter(text: string) {
    // Detener cualquier animación en curso
    if (this.animationInProgress) {
      this.stopAnimation();
    }

    this.animationInProgress = true;

    // Limpiar el elemento
    this.el.nativeElement.textContent = '';

    // Crear y añadir un cursor
    const cursorSpan = document.createElement('span');
    cursorSpan.classList.add('typewriter-cursor');
    cursorSpan.textContent = '';
    this.el.nativeElement.appendChild(cursorSpan);

    // Crear un span para el texto
    const textSpan = document.createElement('span');
    this.el.nativeElement.insertBefore(textSpan, cursorSpan);

    // Iniciar la animación después del retraso
    let charIndex = 0;

    setTimeout(() => {
      // Store interval ID as a class property instead of using dataset
      this.intervalId = window.setInterval(() => {
        if (charIndex < text.length) {
          textSpan.textContent += text[charIndex];
          charIndex++;
        } else {
          this.stopAnimation();
        }
      }, this.typeSpeed);
    }, this.startDelay);
  }

  private stopAnimation() {
    // Clear any existing interval
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    // Reset animation state
    this.animationInProgress = false;

    // Remove cursor element if it exists
    const cursor = this.el.nativeElement.querySelector('.typewriter-cursor');
    if (cursor) {
      cursor.remove();
    }
  }
}
