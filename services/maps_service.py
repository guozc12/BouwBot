from googlemaps import Client
from datetime import datetime, timedelta
from utils.logging_config import logger

class MapsService:
    def __init__(self, api_key: str):
        self.gmaps = Client(key=api_key)
    
    def get_commute_time(self, origin: str, destination: str, mode: str = 'transit', departure_time: int = None) -> dict:
        """查询指定出发时间的通勤信息"""
        if departure_time is None:
            # 默认下周二早上9点
            today = datetime.now()
            days_ahead = (1 - today.weekday() + 7) % 7  # 1=Tuesday
            if days_ahead == 0:
                days_ahead = 7
            next_tuesday = today + timedelta(days=days_ahead)
            commute_time = next_tuesday.replace(hour=9, minute=0, second=0, microsecond=0)
            departure_time = int(commute_time.timestamp())
        
        try:
            directions = self.gmaps.directions(
                origin,
                destination,
                mode=mode,
                departure_time=departure_time,
                region='nl',
                language='nl'
            )
            if directions and len(directions) > 0:
                leg = directions[0]['legs'][0]
                return {
                    'duration': leg['duration']['text'],
                    'distance': leg['distance']['text'],
                    'start_address': leg['start_address'],
                    'end_address': leg['end_address'],
                    'summary': directions[0].get('summary', ''),
                    'mode': mode
                }
        except Exception as e:
            logger.error(f"Error in get_commute_time: {str(e)}")
            return {
                'duration': 'Niet beschikbaar',
                'distance': 'Niet beschikbaar',
                'start_address': origin,
                'end_address': destination,
                'summary': '',
                'mode': mode
            }
    
    def get_nearest_station(self, address: str) -> dict:
        """获取到最近火车站的距离，并查两大通勤点"""
        try:
            # 1. 最近火车站（步行）
            stations = self.gmaps.places_nearby(
                location=self.gmaps.geocode(address)[0]['geometry']['location'],
                radius=5000,
                type='train_station',
                language='nl'
            )
            
            if stations['results']:
                nearest = stations['results'][0]
                station_name = nearest['name']
                station_addr = nearest.get('vicinity', '')
                walk = self.get_commute_time(address, station_name, mode='walking')
            else:
                station_name = ''
                station_addr = ''
                walk = None

            # 2. 到 amsterdam science park station
            science_park = 'Science Park 904, 1098 XH Amsterdam, Netherlands'
            commute_science = self.get_commute_time(address, science_park, mode='transit')

            # 3. 到 Eindhoven Station
            flux_building = 'De Groene Loper 19, 5612 AP Eindhoven, Netherlands'
            commute_flux = self.get_commute_time(address, flux_building, mode='transit')

            return {
                'station_name': station_name,
                'station_addr': station_addr,
                'walking_time': walk['duration'] if walk else '',
                'walking_distance': walk['distance'] if walk else '',
                'to_science_park': commute_science,
                'to_flux': commute_flux
            }
            
        except Exception as e:
            logger.error(f"Error in get_nearest_station: {str(e)}")
            return {
                'station_name': '',
                'station_addr': '',
                'walking_time': '',
                'walking_distance': '',
                'to_science_park': None,
                'to_flux': None
            } 