# WG-Gesucht API Endpoint Reference & Schema Mapping

This document details the internal REST/AJAX contract for WG-Gesucht (`wg-gesucht.de`) ad syndication.

## 1. Authentication & Session Setup
* **Endpoint:** `POST /ajax/sessions.php?action=login`
* **Content-Type:** `application/json`
* **Payload:**
  ```json
  {
    "login_email_username": "<user_email>",
    "login_password": "<user_password>"
  }
  ```
* **Response:**
  * Returns `access_token`, `refresh_token`, `user_id`, `dev_ref_no`, `csrf_token`.
  * Sets session cookies: `PHPSESSID`, `X-Access-Token`, `login_token`, `dev_ref_no`.
* **Subsequent Header Requirements:**
  * `X-Client-Id: wg_desktop_website`
  * `X-User-Id: <user_id>`
  * `X-Authorization: Bearer <access_token>`
  * `x-dev-ref-no: <dev_ref_no>`
  * `Cookie: PHPSESSID=...; X-Access-Token=...; login_token=...`

## 2. Draft Lifecycle
* **Create Draft:** `POST /api/drafts/users/{user_id}`
  * Minimal payload: `ad_title`, `city_id` (`55` for Hamburg), `country_code` (`de`), `category` (`0` for WG-Zimmer), `rent_type` (`0` for Unbefristet), `ad_type` (`0`), `display_language` (`de`), `csrf_token`.
  * Response: Returns `draft_id`.
* **Update Draft:** `PUT /api/drafts/{draft_id}/users/{user_id}`
  * Sets room size, rent, bond/deposit, flatmate demographics, and bilingual descriptions.
* **Publish Offer:** `POST /api/offers/drafts/{draft_id}/users/{user_id}`
  * Converts draft into live ad.

## 3. Photo Management
* **Upload Image:** `POST /api/images/drafts/{draft_id}/users/{user_id}`
* **Payload:**
  ```json
  {
    "images": [
      {
        "filename": "room_01.jpg",
        "position": 1,
        "ad_type": "0",
        "image_base64": "<base64_string>",
        "csrf_token": "<csrf_token>"
      }
    ],
    "csrf_token": "<csrf_token>"
  }
  ```
* **Constraints:** Max 20 photos, JPEG/PNG format, EXIF stripped, aspect preserved within 1920x1080.
