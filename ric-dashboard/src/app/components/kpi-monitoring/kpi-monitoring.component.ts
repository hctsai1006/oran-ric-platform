import { Component, ViewChild, ElementRef } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-kpi-monitoring',
  templateUrl: './kpi-monitoring.component.html',
  styleUrls: ['./kpi-monitoring.component.scss']
})
export class KpiMonitoringComponent {
  @ViewChild('beamIframe') beamIframe?: ElementRef<HTMLIFrameElement>;
  beamUrl: SafeResourceUrl;

  constructor(private sanitizer: DomSanitizer) {
    // Sanitize the URL for iframe embedding
    this.beamUrl = this.sanitizer.bypassSecurityTrustResourceUrl('/beam/');
  }

  refresh(): void {
    // Reload the iframe
    if (this.beamIframe?.nativeElement) {
      this.beamIframe.nativeElement.src = this.beamIframe.nativeElement.src;
    }
  }
}
