from datetime import datetime

from django.http import JsonResponse
from rest_framework.decorators import api_view

from db_connection import db, client
from ..Model_Logic import dict_to_entities
from ..mongoDB import mongoApi, mongo_utils
from .user_veiws import user_authorization

users_collection = db['users']


@api_view(['POST'])
@user_authorization
def add_event(request, user_id):
    if request.method == 'POST':
        with client.start_session() as session:
            try:
                session.start_transaction()
                event = dict_to_entities.create_new_event(request.data)
                date = event.start_time

                if event.frequency == "Once" or event.frequency is None:
                    if mongoApi.add_event(user_id, event, date, session=session):
                        session.commit_transaction()
                        return JsonResponse(event, status=201)
                        # return JsonResponse({'success': 'new event added successfully'}, status=201)

                else:
                    event.first_appearance = date
                    event.item_type = 'recurring event'
                    if mongoApi.add_recurring_event(user_id, event, session=session):
                        session.commit_transaction()
                        return JsonResponse(event.__dict__(), status=201)
                        # return JsonResponse({'success': 'new event added successfully'}, status=201)

                session.abort_transaction()
                return JsonResponse({'error': 'problem adding new event to database'}, status=500)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_event(request, user_id, event_id, date):
    if request.method == 'GET':
        item_type = request.GET.get('item_type')
        if not event_id:
            return JsonResponse({'error': 'missing data'}, status=400)

        with client.start_session() as session:
            try:
                session.start_transaction()
                date = datetime.fromisoformat(date)
                if item_type == 'recurring event':
                    event = mongo_utils.get_recurring_event(user_id, event_id, session=session)
                else:
                    event = mongoApi.get_event(user_id, date, event_id, session=session)
                if event:
                    session.commit_transaction()
                    return JsonResponse(event)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'event not found'}, status=404)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['PUT'])
@user_authorization
def edit_event(request, user_id, event_id, date):
    if request.method == 'PUT':
        data = dict_to_entities.organize_data_edit_event(request.data)
        with client.start_session() as session:
            try:
                session.start_transaction()
                old_date = datetime.fromisoformat(date)
                new_date = old_date if data.get('start_time') is None else datetime.fromisoformat(
                    data.get('start_time'))
                end_date = old_date if data.get('end_time') is None else datetime.fromisoformat(data.get('end_time'))
                if new_date > end_date:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Start comes after end'}, status=400)

                if mongo_utils.update_event(user_id, old_date, new_date, event_id, data, session=session):
                    session.commit_transaction()
                    return JsonResponse({'message': 'Event updated successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Event could not be updated or does not exist'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['DELETE'])
@user_authorization
def delete_event(request, user_id, event_id, date):
    if request.method == 'DELETE':
        item_type = request.GET.get('type') or request.data.get('item_type')
        with client.start_session() as session:
            try:
                session.start_transaction()
                date = datetime.fromisoformat(date)

                if item_type == 'recurring event':
                    result = mongoApi.delete_recurring_event(user_id, event_id, session=session)
                else:
                    result = mongoApi.delete_event(user_id, date, event_id, session=session)

                if result:
                    session.commit_transaction()
                    return JsonResponse({'message': 'Event deleted successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Event not found'}, status=404)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
