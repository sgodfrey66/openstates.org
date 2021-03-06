import stripe
from unittest import mock
import pytest
from django.core.management import call_command
from graphapi.tests.utils import populate_db, populate_unicam


@pytest.mark.django_db
def setup():
    populate_db()
    call_command("update_materialized_views")


@pytest.mark.django_db
def test_state_view(client, django_assert_max_num_queries):
    # difficult to make this one exact, so settled for max of 13, fluctuates between 12-13
    # expected: organization, person, membership, organization, post,
    #   bill, billsponsorship, person, bill, billsponsorship, person,
    #   legislativesession, organization
    with django_assert_max_num_queries(13):
        resp = client.get("/ak/")
    assert resp.status_code == 200
    assert resp.context["state"] == "ak"
    assert resp.context["state_nav"] == "overview"
    assert len(resp.context["chambers"]) == 2

    # check chambers
    ch1, ch2 = resp.context["chambers"]
    if ch1.classification == "upper":
        upper, lower = ch1, ch2
    else:
        lower, upper = ch1, ch2
    assert lower.parties == {"Democratic": 1, "Republican": 3}
    assert lower.seats == 5
    assert lower.committee_count == 0
    assert upper.parties == {"Democratic": 1, "Independent": 1}
    assert upper.seats == 3
    assert upper.committee_count == 0

    # bills
    assert len(resp.context["recently_introduced_bills"]) == 4
    assert len(resp.context["recently_passed_bills"]) == 1

    # sessions
    assert resp.context["all_sessions"][0].identifier == "2018"
    assert (
        resp.context["all_sessions"][0].bill_count
        + resp.context["all_sessions"][1].bill_count
    ) == 12


@pytest.mark.django_db
def test_state_view_unicam(client, django_assert_num_queries):
    populate_unicam()
    resp = client.get("/ne/")
    assert resp.status_code == 200
    assert resp.context["state"] == "ne"
    assert resp.context["state_nav"] == "overview"
    assert len(resp.context["chambers"]) == 1
    legislature = resp.context["chambers"][0]
    assert legislature.parties == {"Nonpartisan": 2}
    assert legislature.seats == 2


@pytest.mark.django_db
def test_homepage(client, django_assert_num_queries):
    with django_assert_num_queries(0):
        resp = client.get("/")
    assert resp.status_code == 200
    assert len(resp.context["states"]) == 52
    assert len(resp.context["blog_updates"])


@pytest.mark.django_db
def test_search(client, django_assert_num_queries):
    with django_assert_num_queries(3):
        resp = client.get("/search/?query=moose")
    assert resp.status_code == 200
    assert len(resp.context["bills"]) == 1
    assert len(resp.context["people"]) == 0

    with django_assert_num_queries(5):
        resp = client.get("/search/?query=amanda")
    assert len(resp.context["bills"]) == 0
    assert len(resp.context["people"]) == 1


@pytest.mark.django_db
def test_donate_success(client):
    with mock.patch("stripe.Charge.create") as charge:
        with mock.patch("stripe.Customer.create") as customer:
            customer.return_value = "~customer~"
            resp = client.post(
                "/donate/",
                {"stripeToken": "abc", "email": "test@example.com", "amount": 100},
            )
            customer.assert_called_once_with(source="abc", email="test@example.com")
            charge.assert_called_once_with(
                customer="~customer~",
                amount="100",
                currency="usd",
                description="Open States Donation",
                metadata={"source": "", "donor_name": ""},
                receipt_email="test@example.com",
            )
            assert resp.status_code == 200
            assert resp.json() == {"success": "OK"}


@pytest.mark.django_db
def test_donate_error(client):
    with mock.patch("stripe.Charge.create") as charge:
        with mock.patch("stripe.Customer.create") as customer:
            customer.side_effect = stripe.error.CardError("error", "error", "error")
            resp = client.post(
                "/donate/",
                {"stripeToken": "abc", "email": "test@example.com", "amount": 100},
            )
            customer.assert_called_once_with(source="abc", email="test@example.com")
            charge.assert_not_called()
            assert resp.status_code == 200
            messages = list(resp.context["messages"])
            assert str(messages[0]) == "error"
