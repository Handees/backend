from pyprembly.data.nigeria import DataVerification
from pyprembly.exceptions import (
    MissingAuthKeyError,
    APIConnectionError,
    MissingRequiredDataError
)
from models.user_models import (
    Kyc, Artisan, KYCEnum
)
from core.extensions import db

from typing import Dict
import uuid


def preformat_data(data):
    _column_aliases = {
        'nin': {'number': 'nin_number'},
        'drivers_license': {'number': 'drivers_license_number'},
        'passport': {'number': 'passport_number'}
    }

    data[_column_aliases[data['kyc_type']]['number']] = data['number']
    del data['number']

    print(data)
    return data


def send_verification_request(data: Dict, artisan: Artisan):
    """
    Sends customer kyc data to Premply
    """
    client = DataVerification()
    _options = {
        'nin': client.nin_face,
        'drivers_license': client.drivers_license_image,
        'passport': client.international_passport_with_face
    }

    try:
        verify_option = _options[data['kyc_type']]

        # prepare data
        to_store = data.copy()
        to_store = preformat_data(to_store)

        new_kyc = Kyc(**to_store)
        new_kyc.kyc_id = str(uuid.uuid4().hex)
        new_kyc.artisan = artisan

        # update artisan kyc status
        artisan.kyc_status = KYCEnum('4')

        # commit transaction
        db.session.add(new_kyc)
        db.session.commit()

        # send to prembly API for verification
        del data['kyc_type']
        stats = verify_option(**data)
        return stats

    except MissingAuthKeyError as e:
        db.session.rollback()
        raise e
    except MissingRequiredDataError as e:
        db.session.rollback()
        raise e
    except APIConnectionError as e:
        db.session.rollback()
        raise e
    else:
        db.session.rollback()
    finally:
        db.session.close()
