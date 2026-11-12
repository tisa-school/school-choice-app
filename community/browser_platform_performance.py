"""Local synthetic budgets, not a claim about deployed Core Web Vitals."""
import json
from pathlib import Path
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import sync_playwright

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PlatformPerformanceBrowserTests(StaticLiveServerTestCase):
    def test_local_home_budgets_mobile_and_desktop(self):
        observations=[]
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            for width in [390,1440]:
                page=browser.new_page(viewport={'width':width,'height':1000})
                page.add_init_script("""window.tkPerf={lcp:null,cls:0};new PerformanceObserver(list=>{for(const e of list.getEntries())window.tkPerf.lcp=e.startTime;}).observe({type:'largest-contentful-paint',buffered:true});new PerformanceObserver(list=>{for(const e of list.getEntries())if(!e.hadRecentInput)window.tkPerf.cls+=e.value;}).observe({type:'layout-shift',buffered:true});""")
                page.goto(self.live_server_url+'/');page.evaluate('document.fonts.ready');page.wait_for_function("performance.getEntriesByName('first-contentful-paint').length>0");page.wait_for_timeout(350)
                result=page.evaluate("""()=>({width:innerWidth,first_contentful_paint_ms:performance.getEntriesByName('first-contentful-paint')[0].startTime,largest_contentful_paint_ms:window.tkPerf.lcp,cumulative_layout_shift:window.tkPerf.cls,decoded_script_bytes:performance.getEntriesByType('resource').filter(e=>e.initiatorType==='script').reduce((sum,e)=>sum+e.decodedBodySize,0),document_bytes:performance.getEntriesByType('navigation')[0].decodedBodySize,document_response_ms:performance.getEntriesByType('navigation')[0].responseEnd})""")
                self.assertLess(result['first_contentful_paint_ms'],2500);self.assertLess(result['decoded_script_bytes'],450000);self.assertLess(result['document_bytes'],500000);self.assertLessEqual(result['cumulative_layout_shift'],.1)
                if result['largest_contentful_paint_ms'] is not None:self.assertLess(result['largest_contentful_paint_ms'],3000)
                observations.append(result);page.close()
            browser.close()
        folder=Path(settings.BASE_DIR)/'docs';folder.mkdir(exist_ok=True)
        (folder/'PLATFORM_V2_LOCAL_PERFORMANCE.json').write_text(json.dumps({'scope':'Local Chromium, isolated test database, no real catalogue photos; not production or field Core Web Vitals','budgets':{'fcp_ms':2500,'lcp_ms':3000,'cls':.1,'decoded_script_bytes':450000,'document_bytes':500000},'inp':'Not measured; requires representative interactions and field validation','observations':observations},indent=2)+'\n')
