import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WozInfoComponent } from './components/woz-info/woz-info.component';
import { WozInfoService } from './services/woz-info.service';

@NgModule({
  declarations: [
    WozInfoComponent
  ],
  imports: [
    CommonModule
  ],
  exports: [
    WozInfoComponent
  ],
  providers: [
    WozInfoService
  ]
})
export class WozInfoModule { } 