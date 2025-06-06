import { Injectable } from '@angular/core';
import { WozInfo } from '../models/woz-info.model';

@Injectable({
  providedIn: 'root'
})
export class WozInfoService {
  parseWozInfo(htmlContent: string): WozInfo {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');
    
    // 提取地址信息
    const address = {
      street: doc.querySelector('#adres-straat')?.textContent?.trim() || '',
      postalCode: doc.querySelector('#adres-postcode')?.textContent?.trim() || '',
      city: doc.querySelector('#adres-woonplaats')?.textContent?.trim() || ''
    };

    // 提取WOZ值
    const wozValues = Array.from(doc.querySelectorAll('.waarden-row')).map(row => ({
      year: row.querySelector('.wozwaarde-datum')?.textContent?.trim() || '',
      value: parseInt(row.querySelector('.wozwaarde-waarde')?.textContent?.replace(/[^0-9]/g, '') || '0')
    }));

    // 提取WOZ详情
    const wozDetails = {
      identification: doc.querySelector('#kenmerk-wozobjectnummer')?.textContent?.trim() || '',
      groundArea: parseInt(doc.querySelector('#kenmerk-grondoppervlakte')?.textContent?.replace(/[^0-9]/g, '') || '0')
    };

    // 提取特征信息
    const characteristics = {
      constructionYear: parseInt(doc.querySelector('#kenmerk-bouwjaar')?.textContent?.trim() || '0'),
      purpose: doc.querySelector('#kenmerk-gebruiksdoel')?.textContent?.trim() || '',
      area: parseInt(doc.querySelector('#kenmerk-oppervlakte')?.textContent?.replace(/[^0-9]/g, '') || '0'),
      addressableObjectId: doc.querySelector('#link-adresseerbaarobjectid')?.getAttribute('href')?.split('=')[1] || '',
      numberIndicationId: doc.querySelector('#link-nummeraanduidingid')?.getAttribute('href')?.split('=')[1] || ''
    };

    // 提取新增的详细信息
    const objectNumber = doc.querySelector('#kenmerk-wozobjectnummer')?.textContent?.trim() || '';
    const groundArea = parseInt(doc.querySelector('#kenmerk-grondoppervlakte')?.textContent?.replace(/[^0-9]/g, '') || '0');
    const buildingYear = parseInt(doc.querySelector('#kenmerk-bouwjaar')?.textContent?.trim() || '0');
    const usage = doc.querySelector('#kenmerk-gebruiksdoel')?.textContent?.trim() || '';
    const area = parseInt(doc.querySelector('#kenmerk-oppervlakte')?.textContent?.replace(/[^0-9]/g, '') || '0');

    // 提取可寻址对象和编号指示信息
    const addressableObjectLink = doc.querySelector('#link-adresseerbaarobjectid');
    const numberIndicationLink = doc.querySelector('#link-nummeraanduidingid');

    const addressableObject = {
      id: addressableObjectLink?.getAttribute('href')?.split('=')[1] || '',
      url: addressableObjectLink?.getAttribute('href') || ''
    };

    const numberIndication = {
      id: numberIndicationLink?.getAttribute('href')?.split('=')[1] || '',
      url: numberIndicationLink?.getAttribute('href') || ''
    };

    return {
      address,
      wozValues,
      wozDetails,
      characteristics,
      objectNumber,
      groundArea,
      buildingYear,
      usage,
      area,
      addressableObject,
      numberIndication
    };
  }

  getWozValueChange(wozInfo: WozInfo): { percentage: number; amount: number } {
    if (wozInfo.wozValues.length < 2) {
      return { percentage: 0, amount: 0 };
    }

    const currentValue = wozInfo.wozValues[0].value;
    const previousValue = wozInfo.wozValues[1].value;
    const amount = currentValue - previousValue;
    const percentage = ((amount / previousValue) * 100);

    return {
      percentage: parseFloat(percentage.toFixed(2)),
      amount
    };
  }
} 