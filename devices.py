import datetime
import requests
import hashlib
import hmac
import os

from models.signin_attempt import SignInAttempts
from flask import request
from loguru import logger
from user_agents import parse
from core import db
from add_extensions import (
    redis_,
    redis_2,
    redis_4,
    redis_7
)


def generate_device_hash():
    try:
        user_agent = parse(request.headers.get("User-Agent", ""))

        device_uuid = (
            request.headers.get("X-Device-UUID", "")
            .strip()
            .lower()
        )
        print("Device UUID:", device_uuid, flush=True)

        device_model = (
            request.headers.get("X-Device-Model", "")
            .strip()
            .lower()
        )
        print("Device Model:", device_model, flush=True)

        device_os = (
            request.headers.get("X-Device-OS")
            or user_agent.os.family
        ).strip().lower()
        print("Device OS:", device_os, flush=True)

        server_secret = os.getenv("DEVICE_HASH_SECRET")

        if not server_secret:
            raise RuntimeError("DEVICE_HASH_SECRET is not configured.")

        raw = f"{device_uuid}|{device_model}|{device_os}"

        device_hash = hmac.new(
            server_secret.encode(),
            raw.encode(),
            hashlib.sha256
        ).hexdigest()

        device_data = {
            "device_uuid": device_uuid,
            "device_model": device_model,
            "device_os": device_os
        }

        return device_hash, device_data

    except Exception:
        logger.exception("Failed to generate device hash")
        raise


def check_device_hash(user):
    try:

        device_hash, _ = generate_device_hash()

        user_id = user.user_id if hasattr(user, "user_id") else user

        pattern = f"device_hash:{user_id}:*"

        keys = redis_.keys(pattern)

        print("Generated hash:", device_hash)
        print("Redis keys:", keys)

        for key in keys:
            saved_hash = key.split(":")[-1]
            
            if saved_hash == device_hash:
                print("Hash matched!")
                return True

        return False

    except Exception:
        logger.exception("Device hash check failed")
        return False
    

def save_device_data(new_user):
    try:
        device_hash, device_data = generate_device_hash()

        redis_key = f"device_hash:{new_user.user_id}:{device_hash}"
        print("Saving device hash in Redis with key:", redis_key, flush=True)

        try:
            redis_.set(
                redis_key,
                "1",
                ex=60 * 60 * 24 * 30
            )
        except Exception:
            logger.exception("Failed to save device hash in Redis")

        signin_data = SignInAttempts(
                        user_id=new_user.user_id,
                        created_at=datetime.datetime.utcnow(),
                        device_uuid=device_data["device_uuid"],
                        device_model=device_data["device_model"],
                        device_os=device_data["device_os"],
                    )

        db.session.add(signin_data)
        db.session.flush()

        new_user.last_seen_id = signin_data.id
        new_user.device_hash = device_hash

        db.session.commit()

        logger.info(
            "Device saved successfully for user_id={}",
            new_user.user_id
        )

        return True

    except Exception:
        db.session.rollback()
        logger.exception(
            "Failed to save device for user_id={}",
            getattr(new_user, "user_id", None)
        )
        return False


# def get_client_ip():
#     try:
#         forwarded = request.headers.get("X-Forwarded-For")

#         if forwarded:
#             return forwarded.split(",")[0].strip()

#         return request.remote_addr

#     except Exception as e:
#         logger.exception("Failed to get client IP: %s", e)
#         return None     

        
def get_estimated_location(ip):
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip}",
            timeout=3
        )

        response.raise_for_status()

        data = response.json()

        return {
            "country": data.get("country"),
            "state": data.get("regionName"),
            "city": data.get("city")
        }

    except requests.exceptions.RequestException as e:
        logger.exception("Failed to fetch estimated location: %s", e)
        return {}

    except Exception as e:
        logger.exception("Unexpected error while fetching estimated location: %s", e)
        return {}