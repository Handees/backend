from tests.base import BaseTestMixin
import json

booking_id = None


class BookingTestCases(BaseTestMixin):
    def test_create_booking(self):
        resp = self.client.post('/bookings/', json={
            "lat": 6.517871336509268,
            "lon": 3.399740067230001,
            "user_id": "jksdhfuihewuiohio2",
            "job_category": "carpentary"
        })
        self.assertEqual(resp.status_code, 201)
        self.assertIn('data', resp.json.keys())
        if 'data' in resp.json.keys():
            global booking_id
            booking_id = resp.json['data']['booking_id']
            self.assertIn(
                'booking_id',
                resp.json['data'].keys()
            )

    def test_fetch_booking(self):
        global booking_id
        resp = self.client.get(f'/bookings/{booking_id}')
        json_response = json.loads(resp.get_data(as_text=True))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('data' in json_response.keys())
        if 'data' in resp.json.keys():
            booking_id = resp.json['data']['booking_id']
            self.assertIn(
                'booking_id',
                resp.json['data'].keys()
            )

    def test_remove_booking(self):
        global booking_id
        resp = self.client.delete(
            f'/bookings/{booking_id}'
        )
        self.assertEqual(200, resp.status_code)

    def test_remove_booking_with_fake_id(self):
        booking_id = "eirjeri320-wije2-30"
        resp = self.client.get(f'/bookings/{booking_id}')
        self.assertEqual(404, resp.status_code)
