// Copyright 2017 The Kubernetes Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import {Component, Inject} from '@angular/core';
import {VersionInfo} from '@api/root.ui';
import {AssetsService} from '@common/services/global/assets';
import {ConfigService} from '@common/services/global/config';
import {HttpClient} from '@angular/common/http';
import {Observable} from 'rxjs';

class Details {
  resourceName = '';
  resourceDetails = '';
}

@Component({
  selector: 'kd-about',
  templateUrl: './template.html',
  styleUrls: ['./style.scss'],
})
export class AboutComponent {
  latestCopyrightYear: number;
  versionInfo: VersionInfo;
  resources: Observable<string[]>;
  resourcesInfo: object;
  apiRoot = 'http://192.168.50.12:8080';
  resourceDetails: Details = new Details();
  isDetailShow: boolean;

  constructor(@Inject(AssetsService) public assets: AssetsService, config: ConfigService, private http: HttpClient) {
    this.versionInfo = config.getVersionInfo();
    this.latestCopyrightYear = new Date().getFullYear();
  }

  ngOnInit() {
    this.http.get<object>(this.apiRoot + '/resources').subscribe(
      response => {
        this.resourcesInfo = response;
        console.log(this.resourcesInfo);
      },
      error => {
        console.log(error);
      }
    );
  }

  pullReasource(_resource: string) {
    this.viewDetails(_resource);
    setTimeout(() => {
      console.log(this.resourceDetails.resourceDetails);
      if(this.resourceDetails.resourceDetails) {
        localStorage.setItem("resource", this.resourceDetails.resourceDetails);
        console.log("details: " + this.resourceDetails.resourceDetails);
      }
      window.location.href = "/#/create";
    }, 300);
  }

  viewDetails(resource: string) {
    if(this.isDetailShow) {
      this.isDetailShow = !this.isDetailShow;
    }else{
      this.isDetailShow = true;
      this.http.get(this.apiRoot + '/resources/' + resource, {responseType: 'text'}).subscribe(
        response => {
          this.resourceDetails.resourceName = ' for ' + resource;
          this.resourceDetails.resourceDetails = response;
          console.log(this.resourceDetails);
        },
        error => {
          console.log(error);
        }
      );
    }
  }
}
