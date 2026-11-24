export interface User {id:number;name:string;role:string;parent:boolean;school:string|null;verified:boolean}
export interface Activity {id:number;title:string;description:string;category:string;venue:string;area:string;start_at:string;end_at:string|null;ages:string;languages:string;price:string;cancelled:boolean;saved:boolean;accessibility:string;listing_type:string;sessions:{id:number;start_at:string;end_at:string;venue:string}[]}
export interface School {id:number;name:string;city:string;curriculum:string;age_label?:string;ages?:string;languages:string;saved?:boolean;web_path:string}
export interface Child {id:number;nickname:string;age_band:string;interests:string;languages:string}
export interface Request {id:number;child:string;event:Activity;status:string;note:string}
export interface CalendarItem {id:string;title:string;start_at:string;end_at:string|null;location:string;cancelled:boolean;web_path:string}
export interface InboxItem {id:number;title:string;message:string;created_at:string;read:boolean;web_path:string}
