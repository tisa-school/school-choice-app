import json
import subprocess
from django.conf import settings
from django.test import TestCase, SimpleTestCase
from .activity_imagery import choose_scene, specification
from . import test_features as fixtures
from .forms import OrganizerSubmissionForm

class ActivitySelectionTests(SimpleTestCase):
    def details(self,**changes):
        item=dict(title='Football practice',description='Friendly football and ball skills.',interest='Sports',area='Campo de Ourique',venue='Local pitch',activityEnvironment='outdoor',minAge=7,maxAge=10)
        item.update(changes);return item

    def test_subject_age_and_setting_are_all_required(self):
        self.assertEqual(choose_scene(self.details()),'football')
        for changes in [dict(title='Basketball',description='Team basketball'),dict(activityEnvironment='indoor'),dict(minAge=13,maxAge=16),dict(minAge=None),dict(venue='',activityEnvironment=''),dict(area='Porto',venue='Local pitch')]:
            self.assertIsNone(choose_scene(self.details(**changes)),changes)
        self.assertIsNone(choose_scene(self.details(title='Lisbon city tour',description='Explore landmarks.',interest='School Life')))

    def test_outdoor_art_uses_park_painting_not_city_or_indoor_art(self):
        details=self.details(title='Art workshop in a park',description='Children painting together in a park.',interest='Arts',minAge=8,maxAge=16,venue='Lisbon park',activityEnvironment='outdoor')
        self.assertEqual(choose_scene(details),'outdoor-painting')
        self.assertIsNone(choose_scene({**details,'venue':'Alfama indoor studio'}))
        self.assertEqual(choose_scene({**details,'activityEnvironment':'','venue':'Lisbon'}),'outdoor-painting')

    def test_specific_subjects_do_not_collapse_into_broad_categories(self):
        self.assertEqual(choose_scene(self.details(title='Paper sculptures',description='Fold paper sculptures together.',interest='Arts',minAge=8,maxAge=16,venue='Alfama studio',activityEnvironment='indoor')),'paper-crafts')
        self.assertIsNone(choose_scene(self.details(title='Piano rhythm lesson',description='Play piano together.',interest='Music',minAge=7,maxAge=9,activityEnvironment='indoor')))
        self.assertIsNone(choose_scene(self.details(title='Video games',description='Play a cooperative game on a console.',interest='Gaming',minAge=10,maxAge=12,activityEnvironment='indoor')))
        self.assertIsNone(choose_scene(self.details(title='Nature bird watching',description='Look for birds and wildlife.',interest='Nature',minAge=8,maxAge=16)))

    def test_server_and_browser_match_the_same_future_listing_details(self):
        cases=[self.details(),self.details(activityEnvironment='indoor'),self.details(title='Draw with watercolour',description='Paint together',interest='Arts',minAge=8,maxAge=16,venue='Studio',activityEnvironment='indoor'),self.details(area='Porto')]
        script="const a=require('./static/community/activity-imagery.js'),s=require('./content/activity-imagery.json');console.log(JSON.stringify(JSON.parse(process.argv[1]).map(e=>a.choose(e,s))));"
        actual=json.loads(subprocess.check_output(['node','-e',script,json.dumps(cases)],cwd=settings.BASE_DIR))
        self.assertEqual(actual,[choose_scene(e) for e in cases])

    def test_curated_seed_selection_is_invalidated_by_event_edits(self):
        script="const a=require('./static/community/activity-imagery.js'),s=require('./content/activity-imagery.json'),events=require('./static/community/demo-state.js').initial().events;console.log(JSON.stringify(events.map(e=>[a.choose(e,s),a.choose({...e,title:{en:'Swimming lesson'},description:{en:'Learn to swim'},interest:'Sports'},s)])));"
        results=json.loads(subprocess.check_output(['node','-e',script],cwd=settings.BASE_DIR))
        self.assertEqual(len({r[0] for r in results}),10)
        self.assertTrue(all(r[1] is None for r in results))

class UploadedImageReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):fixtures.FeatureTests.setUpTestData.__func__(cls)

    def data(self,**changes):
        e=self.event
        data=dict(title='Drawing workshop',category='Arts',listing_type='event',visibility='public',description='Draw Lisbon buildings with watercolours.',venue='Alfama studio',area='Alfama',activity_environment='indoor',min_age=8,max_age=14,start_at=e.start_at.strftime('%Y-%m-%dT%H:%M'),end_at='',time_zone='Europe/Lisbon',image_alt='Children painting with watercolours together at an indoor studio table.',image_source='generated',image_reviewed='on')
        data.update(changes);return data

    def test_review_needs_description_source_and_full_event_context(self):
        self.event.image='events/review-test.jpg';self.event.save()
        for changes,field in [(dict(image_alt=''), 'image_alt'),(dict(image_source='unreviewed'),'image_source'),(dict(min_age=''),'min_age'),(dict(activity_environment=''),'activity_environment')]:
            # Clear old environment when testing an unspecified setting.
            self.event.activity_environment='unspecified'
            form=OrganizerSubmissionForm(self.data(**changes),instance=self.event)
            self.assertFalse(form.is_valid());self.assertIn(field,form.errors)

    def test_commit_false_signs_only_after_saved_filename_and_edits_revoke_review(self):
        self.event.image='events/review-test.jpg';self.event.save()
        form=OrganizerSubmissionForm(self.data(),instance=self.event)
        self.assertTrue(form.is_valid(),form.errors)
        event=form.save(commit=False);event.save();self.assertTrue(event.image_is_reviewed)
        event.venue='Outdoor garden';event.activity_environment='outdoor';event.save()
        self.assertFalse(event.image_is_reviewed)
        event.refresh_from_db();self.assertFalse(event.image_is_reviewed)
        self.assertEqual(event.image.name,'events/review-test.jpg')
