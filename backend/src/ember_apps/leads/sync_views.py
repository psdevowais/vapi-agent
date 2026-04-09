from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class SyncSheetsToDBView(APIView):
    def post(self, request):
        try:
            call_command('sync_sheets_to_db')
            return Response({'status': 'success', 'message': 'Sync completed successfully'})
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
