from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

class AdditiveMigrationTests(TransactionTestCase):
    def test_existing_school_data_preserved_and_private(self):
        old=('community','0002_privateupload')
        target=('community','0003_event_accessibility_event_area_and_more')
        executor=MigrationExecutor(connection)
        executor.migrate([old])
        try:
            state=executor.loader.project_state([old]).apps
            User=state.get_model('auth','User');School=state.get_model('community','School');Event=state.get_model('community','Event')
            Ticket=state.get_model('community','TicketRequest');Saved=state.get_model('community','SavedEvent')
            user=User.objects.create(username='legacy-user')
            school=School.objects.create(name='Legacy school',invite_code_hash='unchanged-test-hash',time_zone='America/Toronto')
            from django.utils import timezone
            event=Event.objects.create(school=school,created_by=user,title='Legacy event',category='Music',description='Preserve this content',venue='Original venue',start_at=timezone.now(),capacity=12,status='published')
            ticket=Ticket.objects.create(event=event,student=user,status='approved')
            saved=Saved.objects.create(user=user,event=event)
            executor=MigrationExecutor(connection);executor.migrate([target])
            current=executor.loader.project_state([target]).apps
            restored=current.get_model('community','Event').objects.get(pk=event.pk)
            self.assertEqual(restored.visibility,'school');self.assertIsNone(restored.published_by_id)
            self.assertEqual(restored.time_zone,'America/Toronto');self.assertEqual(restored.description,'Preserve this content')
            self.assertEqual(current.get_model('community','TicketRequest').objects.get(pk=ticket.pk).status,'approved')
            self.assertEqual(current.get_model('community','SavedEvent').objects.get(pk=saved.pk).event_id,event.pk)
            self.assertEqual(current.get_model('community','School').objects.get(pk=school.pk).invite_code_hash,'unchanged-test-hash')
        finally:
            MigrationExecutor(connection).migrate([target])
