import redis
import json
import threading
import time
from typing import Dict


class CarlaRedisClient:
    def __init__(self, host='192.168.79.133', port=6379, db=0, password=11111111):
        self.pool = redis.ConnectionPool(host=host, port=port, db=db, password=password)
        self.r = redis.Redis(connection_pool=self.pool)
        self.status_updaters: Dict[str, 'StatusUpdater'] = {}
        self.lock = threading.Lock()

    def serialize_transform(self, transform) -> dict:
        """序列化Carla坐标变换"""
        return {
            'x': transform.location.x,
            'y': transform.location.y,
            'z': transform.location.z,
            'pitch': transform.rotation.pitch,
            'yaw': transform.rotation.yaw,
            'roll': transform.rotation.roll
        }

    def serialize_control(self, control) -> dict:
        """序列化控制指令"""
        return {
            'throttle': control.throttle,
            'steer': control.steer,
            'brake': control.brake,
            'reverse': control.reverse
        }

    def update_vehicle_status(self, vehicle_id: str, status: dict):
        """更新车辆状态到Redis"""
        try:
            self.r.hset("carla:vehicle:status", vehicle_id, json.dumps(status))
        except redis.RedisError as e:
            print(f"[Redis] 状态更新失败: {str(e)}")


class StatusUpdater(threading.Thread):
    def __init__(self, client: CarlaRedisClient, vehicle):
        super().__init__()
        self.client = client
        self.vehicle = vehicle
        self.running = True

    def run(self):
        print(f"[StatusUpdater] 启动线程: {self.vehicle.id}")
        while self.running:
            status = {
                'timestamp': time.time(),
                'transform': self.client.serialize_transform(self.vehicle.get_transform()),
                'velocity': {
                    'x': self.vehicle.get_velocity().x,
                    'y': self.vehicle.get_velocity().y,
                    'z': self.vehicle.get_velocity().z
                },
                'control': self.client.serialize_control(self.vehicle.get_control()),
                'collision': getattr(self.vehicle, 'collision_flag', False),
                'is_avoiding': getattr(self.vehicle, 'is_avoiding', False)
            }
            self.client.update_vehicle_status(self.vehicle.id, status)
            time.sleep(0.1)
        print(f"[StatusUpdater] 停止线程: {self.vehicle.id}")

    def stop(self):
        self.running = False