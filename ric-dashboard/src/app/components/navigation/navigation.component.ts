import { Component } from '@angular/core';

export interface NavItem {
  icon: string;
  label: string;
  route: string;
}

@Component({
  selector: 'app-navigation',
  templateUrl: './navigation.component.html',
  styleUrls: ['./navigation.component.scss']
})
export class NavigationComponent {
  navItems: NavItem[] = [
    { icon: 'dashboard', label: '平台概覽', route: '/dashboard' },
    { icon: 'apps', label: 'xApps 管理', route: '/xapps' },
    { icon: 'analytics', label: 'KPI 監控', route: '/kpi' },
    { icon: 'insert_chart', label: 'Grafana 儀表板', route: '/grafana' },
    { icon: 'sync_alt', label: '雙路徑監控', route: '/dual-path' },
    { icon: 'notifications', label: '告警通知', route: '/alerts' }
  ];

  platformInfo = {
    name: 'O-RAN RIC Platform',
    version: '',
    lab: 'MBWCL'
  };
}
