import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

interface XApp {
  name: string;
  namespace: string;
  replicas: number;
  ready_replicas: number;
  status: string;
  version: string;
  health: {
    alive: boolean;
    ready: boolean;
  };
}

@Component({
  selector: 'app-xapps-management',
  templateUrl: './xapps-management.component.html',
  styleUrls: ['./xapps-management.component.scss']
})
export class XappsManagementComponent implements OnInit {
  xapps: XApp[] = [];
  loading = true;
  error: string | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadXApps();
  }

  loadXApps(): void {
    this.loading = true;
    this.error = null;
    
    this.http.get<XApp[]>('/api/xapps').subscribe({
      next: (xapps) => {
        this.xapps = xapps;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load xApps: ' + err.message;
        this.loading = false;
      }
    });
  }

  refresh(): void {
    this.loadXApps();
  }
}
