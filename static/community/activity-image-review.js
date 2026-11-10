/* Reviewing an upload is a human attestation, never an automated vision claim. */
document.addEventListener('DOMContentLoaded',()=>{
 const form=document.getElementById('event-form'),review=form?.elements.namedItem('image_reviewed');if(!review)return;
 const relevant=new Set(['title','description','category','min_age','max_age','venue','area','address','activity_environment','image','image_alt','image_source']);
 const updatePreview=()=>{const target=document.getElementById('image-review-preview'),fresh=document.getElementById('upload-preview'),old=form.querySelector('.upload-preview:not(#upload-preview):not(#image-review-preview)'),source=fresh&&!fresh.hidden?fresh.src:old?.src;if(!target)return;target.hidden=!source;if(source)target.src=source;target.alt=form.elements.namedItem('image_alt')?.value||'Uploaded image awaiting descriptive alt text';};
 const changed=event=>{if(relevant.has(event.target.name)){review.checked=false;updatePreview();}};form.addEventListener('input',changed);form.addEventListener('change',changed);updatePreview();
});
