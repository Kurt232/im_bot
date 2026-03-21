"""Tests for email parser."""

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from im_bot_email.parser import parse_email, _decode_header_value, _strip_html


def _simple_email(subject="Test", body="Hello world"):
    """Create a simple plain-text email."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "alice@example.com"
    msg["To"] = "bot@example.com"
    return msg


def test_parse_plain_text():
    msg = _simple_email("My Task", "Do something important")
    parsed = parse_email(msg)

    assert parsed.subject == "My Task"
    assert parsed.sender == "alice@example.com"
    assert parsed.body == "Do something important"
    assert parsed.attachments == []


def test_parse_html_only():
    msg = MIMEText("<p>Hello <b>world</b></p>", "html")
    msg["Subject"] = "HTML email"
    msg["From"] = "bob@example.com"
    parsed = parse_email(msg)

    assert parsed.body == "Hello world"


def test_parse_multipart_prefers_plain():
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Multi"
    msg["From"] = "carol@example.com"
    msg.attach(MIMEText("Plain version", "plain"))
    msg.attach(MIMEText("<p>HTML version</p>", "html"))

    parsed = parse_email(msg)
    assert parsed.body == "Plain version"


def test_parse_multipart_falls_back_to_html():
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "HTML only multi"
    msg["From"] = "dave@example.com"
    msg.attach(MIMEText("<p>Only HTML</p>", "html"))

    parsed = parse_email(msg)
    assert parsed.body == "Only HTML"


def test_parse_attachment():
    msg = MIMEMultipart()
    msg["Subject"] = "With attachment"
    msg["From"] = "eve@example.com"
    msg.attach(MIMEText("See attached"))

    att = MIMEBase("application", "octet-stream")
    att.set_payload(b"file content here")
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", "attachment", filename="data.txt")
    msg.attach(att)

    parsed = parse_email(msg)
    assert parsed.body == "See attached"
    assert len(parsed.attachments) == 1
    assert parsed.attachments[0].filename == "data.txt"
    assert parsed.attachments[0].content == b"file content here"


def test_parse_multiple_attachments():
    msg = MIMEMultipart()
    msg["Subject"] = "Two files"
    msg["From"] = "frank@example.com"
    msg.attach(MIMEText("body"))

    for name in ["a.txt", "b.pdf"]:
        att = MIMEBase("application", "octet-stream")
        att.set_payload(b"x")
        encoders.encode_base64(att)
        att.add_header("Content-Disposition", "attachment", filename=name)
        msg.attach(att)

    parsed = parse_email(msg)
    assert len(parsed.attachments) == 2
    assert {a.filename for a in parsed.attachments} == {"a.txt", "b.pdf"}


def test_to_task_description_no_attachments():
    msg = _simple_email("Deploy v2", "Please deploy version 2")
    parsed = parse_email(msg)
    desc = parsed.to_task_description()

    assert "Subject: Deploy v2" in desc
    assert "From: alice@example.com" in desc
    assert "Please deploy version 2" in desc
    assert "Attachments" not in desc


def test_to_task_description_with_attachments():
    msg = MIMEMultipart()
    msg["Subject"] = "Report"
    msg["From"] = "grace@example.com"
    msg.attach(MIMEText("Attached"))

    att = MIMEBase("application", "octet-stream")
    att.set_payload(b"data")
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", "attachment", filename="report.csv")
    msg.attach(att)

    desc = parse_email(msg).to_task_description()
    assert "[Attachments: report.csv]" in desc


def test_decode_rfc2047_header():
    # RFC 2047 encoded UTF-8 subject
    assert _decode_header_value("=?utf-8?B?5L2g5aW9?=") == "你好"


def test_decode_header_none():
    assert _decode_header_value(None) == ""


def test_strip_html_entities():
    assert _strip_html("a &amp; b &lt; c") == "a & b < c"


def test_strip_html_br_tags():
    assert _strip_html("line1<br>line2<br/>line3") == "line1\nline2\nline3"


def test_no_subject():
    msg = MIMEText("body")
    msg["From"] = "x@example.com"
    parsed = parse_email(msg)
    assert parsed.subject == ""
