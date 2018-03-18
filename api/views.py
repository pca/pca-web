"""
We use APIView in all endpoints instead of the magical generic views in
favor of code readability/visualization of what's happening in each
endpoint. It will also help people with less/zero knowledge of the framework
contribute easily without knowing what those generic views are for.
"""
import phgeograpy
from rest_framework.response import Response
from rest_framework.views import APIView

from wca.client import WCAClient

wca_client = WCAClient()


class ListRegions(APIView):
    """
    View to list all supported (with rankings) regions in the Philippines.
    """

    def get(self, request, *args, **kwargs):
        regions = phgeograpy.regions()
        results = []

        for region in regions:
            results.append({
                'id': region.slug,
                'name': region.name,
                'description': region.description,
            })

        data = {
            'results': results,
        }
        return Response(data)


class ListCitiesProvinces(APIView):
    """
    View to list all supported (with rankings) cities in Metro Manila
    and provinces (excluding Metro Manila) all over the Philippines.
    """

    def get(self, request, *args, **kwargs):
        results = []

        # Get cities in Metro Manila
        region = phgeograpy.regions('ncr')
        province = region.provinces()[0]
        cities = province.municipalities()

        for city in cities:
            results.append({
                'id': city.slug,
                'name': city.name,
            })

        # Get provinces
        provinces = phgeograpy.provinces()

        for province in provinces:
            # Exclude Metro Manila
            if province.slug != 'metro_manila':
                results.append({
                    'id': province.slug,
                    'name': province.name,
                })

        data = {
            'results': results,
        }
        return Response(data)


class ListCompetitions(APIView):
    """
    View to list all upcoming competitions in the Philippines.
    """

    def get(self, request, *args, **kwargs):
        data = {
            'results': wca_client.competitions(),
        }
        return Response(data)


class ListNationalRankings(APIView):
    """
    View to list the top 10 rankings of event(s) in national level.

    Args:
        events: A comma-separated list of events. If no `events`
            were requested, all rankings for all events will
            be returned.
        type: Ranking type can be `all`, `single`, or `average`.
    """

    def get(self, request, *args, **kwargs):
        events = request.query_params.get('events')
        rank_type = request.query_params.get('type')
        rankings = {}

        if events:
            events = events.split(',')

            for event in events:
                if rank_type == 'single' or rank_type == 'all':
                    best_rankings = wca_client.rankings(event, 'best', 'national')
                    rankings['single_{}'.format(event)] = best_rankings

                if rank_type == 'average' or rank_type == 'all':
                    average_rankings = wca_client.rankings(event, 'average', 'nationa')
                    rankings['average_{}'.format(event)] = average_rankings
        else:
            rankings = wca_client.all_rankings('national')

        data = {
            'results': rankings,
        }
        return Response(data)


class ListRegionalRankings(APIView):
    """
    View to list the top 10 rankings of event(s) in regional level.
    """

    def get(self, request, *args, **kwargs):
        return Response({})


class ListCityProvincialRankings(APIView):
    """
    View to list the top 10 rankings of event(s) in city/provincial level.
    """

    def get(self, request, *args, **kwargs):
        return Response({})
