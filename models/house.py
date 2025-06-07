from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class StationInfo:
    name: str
    address: str
    walking_time: str
    walking_distance: str
    to_science_park: Optional[Dict]
    to_flux: Optional[Dict]

@dataclass
class HouseInfo:
    title: str
    address: str
    price: str
    size_rooms: str
    agent: str
    images: List[str]
    url: str
    details: str
    details_sections: Dict
    agent_info: Dict
    important_info: Dict
    nearest_station: StationInfo
    woz_info: Optional[str]
    immigration_info: Optional[str]
    huispedia_url: Optional[str]
    filename: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict) -> 'HouseInfo':
        """从字典创建HouseInfo实例"""
        station_data = data.get('nearest_station', {})
        station_info = StationInfo(
            name=station_data.get('station_name', ''),
            address=station_data.get('station_addr', ''),
            walking_time=station_data.get('walking_time', ''),
            walking_distance=station_data.get('walking_distance', ''),
            to_science_park=station_data.get('to_science_park'),
            to_flux=station_data.get('to_flux')
        )
        
        return cls(
            title=data.get('title', ''),
            address=data.get('address', ''),
            price=data.get('price', ''),
            size_rooms=data.get('size_rooms', ''),
            agent=data.get('agent', ''),
            images=data.get('images', []),
            url=data.get('url', ''),
            details=data.get('details', ''),
            details_sections=data.get('details_sections', {}),
            agent_info=data.get('agent_info', {}),
            important_info=data.get('important_info', {}),
            nearest_station=station_info,
            woz_info=data.get('woz_info'),
            immigration_info=data.get('immigration_info'),
            huispedia_url=data.get('huispedia_url'),
            filename=data.get('filename')
        ) 