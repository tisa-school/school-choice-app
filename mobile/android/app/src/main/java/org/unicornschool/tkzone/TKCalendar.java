package org.unicornschool.tkzone;

import android.content.Intent;
import android.provider.CalendarContract;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.JSObject;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.text.SimpleDateFormat;
import java.util.Locale;

@CapacitorPlugin(name="TKCalendar")
public class TKCalendar extends Plugin {
    @PluginMethod public void present(PluginCall call){
        try{
            // No READ_CALENDAR or WRITE_CALENDAR permission: the adult reviews the system editor.
            SimpleDateFormat parser=new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX",Locale.ROOT);
            long start=parser.parse(call.getString("start").replaceAll("\\.\\d+","")).getTime();
            long end=parser.parse(call.getString("end").replaceAll("\\.\\d+","")).getTime();
            if(end<=start)throw new IllegalArgumentException();
            Intent intent=new Intent(Intent.ACTION_INSERT).setData(CalendarContract.Events.CONTENT_URI)
                .putExtra(CalendarContract.Events.TITLE,call.getString("title"))
                .putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME,start).putExtra(CalendarContract.EXTRA_EVENT_END_TIME,end)
                .putExtra(CalendarContract.Events.EVENT_LOCATION,call.getString("location"))
                .putExtra(CalendarContract.Events.DESCRIPTION,"Family plan, not a booking. "+call.getString("url",""));
            getActivity().startActivity(intent);JSObject result=new JSObject();result.put("opened",true);call.resolve(result);
        }catch(Exception ignored){call.reject("A compatible calendar app and valid dates are required.");}
    }
}
