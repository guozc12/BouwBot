import { Component, Input } from '@angular/core';
import { WozInfo } from '../../models/woz-info.model';
import { WozInfoService } from '../../services/woz-info.service';

@Component({
  selector: 'app-woz-info',
  template: `
    <div class="woz-info-container">
      <section class="address-section">
        <h2>Adres</h2>
        <address>
          {{ wozInfo.address.street }}<br>
          {{ wozInfo.address.postalCode }} {{ wozInfo.address.city }}
        </address>
      </section>

      <section class="woz-values-section">
        <h2>WOZ-waarde</h2>
        <table class="woz-values-table">
          <thead>
            <tr>
              <th>Peildatum</th>
              <th>WOZ-waarde</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let value of wozInfo.wozValues">
              <td>{{ value.year }}</td>
              <td>{{ value.value | number:'1.0-0' }} euro</td>
            </tr>
          </tbody>
        </table>
        <div class="value-change" *ngIf="valueChange">
          <p>Verandering t.o.v. vorig jaar: {{ valueChange.percentage }}% ({{ valueChange.amount | number:'1.0-0' }} euro)</p>
        </div>
      </section>

      <section class="woz-details-section">
        <h2>WOZ-gegevens</h2>
        <dl>
          <dt>Identificatie:</dt>
          <dd>{{ wozInfo.objectNumber }}</dd>
          
          <dt>Grondoppervlakte:</dt>
          <dd>{{ wozInfo.groundArea }}m²</dd>
        </dl>
      </section>

      <section class="characteristics-section">
        <h2>Kenmerken</h2>
        <dl>
          <dt>Bouwjaar:</dt>
          <dd>{{ wozInfo.buildingYear }}</dd>
          
          <dt>Gebruiksdoel:</dt>
          <dd>{{ wozInfo.usage }}</dd>
          
          <dt>Oppervlakte:</dt>
          <dd>{{ wozInfo.area }}m²</dd>
          
          <dt>Adresseerbaar object:</dt>
          <dd>
            <a [href]="wozInfo.addressableObject.url" target="_blank" rel="noopener noreferrer">
              {{ wozInfo.addressableObject.id }}
              <span class="external-link-icon">↗</span>
            </a>
          </dd>
          
          <dt>Nummeraanduiding:</dt>
          <dd>
            <a [href]="wozInfo.numberIndication.url" target="_blank" rel="noopener noreferrer">
              {{ wozInfo.numberIndication.id }}
              <span class="external-link-icon">↗</span>
            </a>
          </dd>
        </dl>
      </section>
    </div>
  `,
  styles: [`
    .woz-info-container {
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
    }

    section {
      margin-bottom: 30px;
    }

    h2 {
      color: #333;
      margin-bottom: 15px;
    }

    .woz-values-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 15px;
    }

    .woz-values-table th,
    .woz-values-table td {
      padding: 10px;
      border: 1px solid #ddd;
      text-align: left;
    }

    .woz-values-table th {
      background-color: #f5f5f5;
    }

    .value-change {
      background-color: #f8f9fa;
      padding: 10px;
      border-radius: 4px;
    }

    dl {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 10px;
    }

    dt {
      font-weight: bold;
      color: #666;
    }

    address {
      font-style: normal;
      line-height: 1.6;
    }

    a {
      color: #0066cc;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    a:hover {
      text-decoration: underline;
    }

    .external-link-icon {
      font-size: 0.8em;
      opacity: 0.7;
    }
  `]
})
export class WozInfoComponent {
  @Input() wozInfo!: WozInfo;
  valueChange: { percentage: number; amount: number } | null = null;

  constructor(private wozInfoService: WozInfoService) {}

  ngOnInit() {
    this.valueChange = this.wozInfoService.getWozValueChange(this.wozInfo);
  }
} 