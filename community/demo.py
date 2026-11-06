"""Registration-free Tech Week presentation. No accounts or application records are created."""
from datetime import timedelta
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_safe

@require_safe
def presentation(request, section='home', item=''):
    if section not in {'home','events','activities','detail','family','organizer','creator','saved','finder','calendar'}:
        raise Http404()
    today=timezone.localdate()
    def listing(id,title,category,kind,days,venue,description,capacity):
        return {'id':id,'title':title,'category':category,'kind':kind,'day':str(today+timedelta(days=days)),'time':'15:30','endTime':'17:00','venue':venue,'area':'Lisbon','address':'Illustrative venue — not a real event location','description':description,'minAge':7,'maxAge':12,'languages':'English, Portuguese','capacity':capacity,'price':'Price on request','image':'','contact':'Demo activity team','phone':'','website':'','status':'published','environment':'indoor','demo':True}
    catalog=[
        listing('art-afternoon','Creative Art Afternoon','Arts','event',3,'Demo Arts Studio','A sample afternoon of drawing and creative projects. All listing details are fictional and are shown only for the Tech Week presentation.',12),
        listing('science-lab','Little Discoveries Lab','Science','event',5,'Demo Discovery Room','Try the event request and approval flow with this fictional science activity. No real booking is made.',8),
        listing('music-meetup','Make Some Music','Music','event',7,'Demo Music Space','A sample community music event for exploring shared interests. This is demonstration content, not an advertised school event.',10),
        listing('creative-club','Creative Makers Club','Arts','activity',4,'Demo Makers Room','An example of an ongoing activity. This demo represents one session; joining does not reserve future sessions.',8),
        listing('nature-club','Nature Explorers','Nature','activity',6,'Demo Outdoor Classroom','A fictional activity for trying filters and family planning. No real venue, supervision, or availability is promised.',10),
        listing('gaming-together','Game Together Afternoon','Gaming','event',8,'Demo Games Room','A fictional board-game and friendly gaming session for the presentation. No actual competition or booking is advertised.',10),
        listing('family-market','Family Makers Market','Shopping','event',9,'Demo Community Market','A fictional family-friendly market example. No real sellers, prices, or venue are represented.',20),
        listing('theater-workshop','Stories on Stage','Theater & Drama','activity',10,'Demo Theater Studio','A fictional drama and storytelling workshop for trying category and language discovery.',12),
    ]
    response=render(request,'community/demo.html',{'demo_section':section,'demo_item':item,'demo_catalog':catalog})
    response['Cache-Control']='no-store'
    response['X-Robots-Tag']='noindex, nofollow'
    return response
