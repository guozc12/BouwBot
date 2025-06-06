export interface WozInfo {
  address: {
    street: string;
    postalCode: string;
    city: string;
  };
  wozValues: {
    year: string;
    value: number;
  }[];
  wozDetails: {
    identification: string;
    groundArea: number;
  };
  characteristics: {
    constructionYear: number;
    purpose: string;
    area: number;
    addressableObjectId: string;
    numberIndicationId: string;
  };
  objectNumber: string;
  groundArea: number;
  buildingYear: number;
  usage: string;
  area: number;
  addressableObject: {
    id: string;
    url: string;
  };
  numberIndication: {
    id: string;
    url: string;
  };
} 