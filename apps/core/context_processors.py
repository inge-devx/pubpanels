from apps.agencies.models import Agency


def active_agency(request):
    slug = request.session.get("confined_agency_slug")
    if not slug:
        return {"confined_agency": None}

    agency = Agency.objects.filter(slug=slug, status=Agency.Status.ACTIVE).first()
    return {"confined_agency": agency}