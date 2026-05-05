from __future__ import annotations

from conftest import configure_test_environment


configure_test_environment("learning-english-api-main-chain-")


def test_stub_parent_login_upload_reaches_ai_review(api_client) -> None:
    login_response = api_client.post(
        "/v1/auth/wechat/login",
        json={"auth_code": "main-chain-parent"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["status"] == "phone_binding_required"
    bind_token = login_payload["bind_token"]

    otp_response = api_client.post(
        "/v1/auth/phone/request-otp",
        json={"bind_token": bind_token, "phone_number": "13800138001"},
    )
    assert otp_response.status_code == 200
    otp_payload = otp_response.json()
    assert otp_payload["debug_code"] == "123456"

    bind_response = api_client.post(
        "/v1/auth/phone/bind",
        json={
            "bind_token": bind_token,
            "phone_number": "13800138001",
            "otp_code": otp_payload["debug_code"],
        },
    )
    assert bind_response.status_code == 200
    bind_payload = bind_response.json()
    assert bind_payload["status"] == "authenticated"
    access_token = bind_payload["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "喜欢动物主题",
        },
        headers=headers,
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    upload_response = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-04-29",
            "title": "Animals Around Me",
            "topic": "动物",
            "tags": "动物,MVP",
        },
        files=[
            (
                "files",
                (
                    "worksheet.jpg",
                    b"fake image bytes with cat dog bird words",
                    "image/jpeg",
                ),
            )
        ],
        headers=headers,
    )
    assert upload_response.status_code == 201
    created = upload_response.json()
    assert created["material"]["status"] == "processing"
    material_id = created["material"]["id"]
    job_id = created["job"]["id"]

    job_response = api_client.get(f"/v1/material-jobs/{job_id}", headers=headers)
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "needs_review"
    assert job["material_id"] == material_id
    assert job["draft_title"]
    assert job["draft_topic"]
    assert job["draft_vocabulary"]

    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    material = material_response.json()["material"]
    assert material["id"] == material_id
    assert material["status"] == "needs_review"


def test_upload_poll_confirm_preserves_image_level_records(api_client) -> None:
    login_response = api_client.post(
        "/v1/auth/wechat/login",
        json={"auth_code": "image-record-parent"},
    )
    assert login_response.status_code == 200
    bind_token = login_response.json()["bind_token"]
    otp_response = api_client.post(
        "/v1/auth/phone/request-otp",
        json={"bind_token": bind_token, "phone_number": "13800138002"},
    )
    bind_response = api_client.post(
        "/v1/auth/phone/bind",
        json={
            "bind_token": bind_token,
            "phone_number": "13800138002",
            "otp_code": otp_response.json()["debug_code"],
        },
    )
    headers = {"Authorization": f"Bearer {bind_response.json()['tokens']['access_token']}"}

    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "",
        },
        headers=headers,
    )
    child_id = child_response.json()["id"]

    upload_response = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-05-05",
            "title": "Run, Hop, Go!",
            "topic": "phonics",
            "file_sources": ["camera", "gallery"],
        },
        files=[
            ("files", ("rr.jpg", b"Rr worksheet image", "image/jpeg")),
            ("files", ("qq.jpg", b"Qq worksheet image", "image/jpeg")),
        ],
        headers=headers,
    )
    assert upload_response.status_code == 201
    created = upload_response.json()
    material_id = created["material"]["id"]
    job_id = created["job"]["id"]

    image_records = created["material"]["image_records"]
    assert [(item["page_index"], item["source_type"], item["original_filename"]) for item in image_records] == [
        (1, "camera", "rr.jpg"),
        (2, "gallery", "qq.jpg"),
    ]
    assert all(item["url"] and item["object_key"] and item["content_type"] for item in image_records)

    job_response = api_client.get(f"/v1/material-jobs/{job_id}", headers=headers)
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "needs_review"
    assert len(job["draft_image_records"]) == 2
    assert all(item["image_title"] for item in job["draft_image_records"])
    assert all(item["vocabulary"] for item in job["draft_image_records"])
    assert all(item["sentences"] for item in job["draft_image_records"])
    assert all(item["details"] for item in job["draft_image_records"])

    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    material = material_response.json()["material"]
    assert len(material["image_records"]) == 2
    assert all(item["image_title"] for item in material["image_records"])

    confirm_response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={},
        headers=headers,
    )
    assert confirm_response.status_code == 200

    knowledge_response = api_client.get(f"/v1/knowledge-packs/{material_id}", headers=headers)
    assert knowledge_response.status_code == 200
    assert len(knowledge_response.json()["material"]["image_records"]) == 2
