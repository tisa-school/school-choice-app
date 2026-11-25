import UIKit
import Capacitor
import Security
import EventKit
import EventKitUI

class TKBridgeViewController: CAPBridgeViewController {
    override func capacitorDidLoad() {
        bridge?.registerPluginInstance(TKSecureStorage())
        bridge?.registerPluginInstance(TKCalendar())
    }
}

@objc(TKSecureStorage)
public class TKSecureStorage: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "TKSecureStorage"
    public let jsName = "TKSecureStorage"
    public let pluginMethods: [CAPPluginMethod] = [CAPPluginMethod(name:"read",returnType:CAPPluginReturnPromise),CAPPluginMethod(name:"write",returnType:CAPPluginReturnPromise),CAPPluginMethod(name:"clear",returnType:CAPPluginReturnPromise)]
    private var query: [String:Any] { [kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:"org.unicornschool.tkzone",kSecAttrAccount as String:"mobile-session"] }
    @objc func read(_ call: CAPPluginCall) {
        var q=query;q[kSecReturnData as String]=true;q[kSecMatchLimit as String]=kSecMatchLimitOne
        var result: CFTypeRef?;let status=SecItemCopyMatching(q as CFDictionary,&result)
        if status==errSecItemNotFound { call.resolve(["value":NSNull()]);return }
        guard status==errSecSuccess,let data=result as? Data,let value=String(data:data,encoding:.utf8) else {call.reject("Secure session unavailable. Sign in again.");return}
        call.resolve(["value":value])
    }
    @objc func write(_ call: CAPPluginCall) {
        guard let value=call.getString("value"),value.count<=200 else {call.reject("Invalid session.");return}
        SecItemDelete(query as CFDictionary);var q=query
        q[kSecValueData as String]=Data(value.utf8);q[kSecAttrAccessible as String]=kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        guard SecItemAdd(q as CFDictionary,nil)==errSecSuccess else {call.reject("Secure session storage unavailable.");return};call.resolve()
    }
    @objc func clear(_ call: CAPPluginCall) {
        let status=SecItemDelete(query as CFDictionary)
        if status==errSecSuccess||status==errSecItemNotFound {call.resolve()}else{call.reject("Could not clear session.")}
    }
}

@objc(TKCalendar)
public class TKCalendar: CAPPlugin, CAPBridgedPlugin, EKEventEditViewDelegate {
    public let identifier="TKCalendar"
    public let jsName="TKCalendar"
    public let pluginMethods:[CAPPluginMethod]=[CAPPluginMethod(name:"present",returnType:CAPPluginReturnPromise)]
    private let store=EKEventStore()
    private var pending:CAPPluginCall?
    private func date(_ value:String?) -> Date? {
        guard let value=value else{return nil}
        let parser=ISO8601DateFormatter();parser.formatOptions=[.withInternetDateTime,.withFractionalSeconds]
        if let date=parser.date(from:value){return date};parser.formatOptions=[.withInternetDateTime];return parser.date(from:value)
    }
    @objc func present(_ call:CAPPluginCall) {
        guard pending==nil,let start=date(call.getString("start")),let end=date(call.getString("end")),end>start else {call.reject("Valid start and end times are required.");return}
        pending=call
        let completion:(Bool,Error?)->Void={granted,_ in DispatchQueue.main.async {
            guard granted else{self.pending=nil;call.reject("Calendar permission was not granted.");return}
            let event=EKEvent(eventStore:self.store);event.title=call.getString("title");event.startDate=start;event.endDate=end;event.location=call.getString("location");event.notes="Family plan, not a booking.";event.url=URL(string:call.getString("url") ?? "")
            let editor=EKEventEditViewController();editor.eventStore=self.store;editor.event=event;editor.editViewDelegate=self
            self.bridge?.viewController?.present(editor,animated:true)
        }}
        if #available(iOS 17.0,*) { store.requestWriteOnlyAccessToEvents(completion:completion) }
        else { store.requestAccess(to:.event,completion:completion) }
    }
    public func eventEditViewController(_ controller:EKEventEditViewController,didCompleteWith action:EKEventEditViewAction) {
        controller.dismiss(animated:true);pending?.resolve(["opened":true,"saved":action == .saved]);pending=nil
    }
}
