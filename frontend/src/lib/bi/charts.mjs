export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const palette=['#2563eb','#7c3aed','#0891b2','#f59e0b','#10b981','#e05a76'];
const number=new Intl.NumberFormat('es-PE',{maximumFractionDigits:1});
export function formatValue(value,unit='') {
  if(value == null || !Number.isFinite(value)) return 'Sin datos';
  if(['%','percent','rate','porcentaje'].includes(unit)) return `${number.format(value*100)}%`;
  return `${number.format(value)}${unit ? ' '+unit : ''}`;
}
const text=(x,y,value,extra='')=>`<text x="${x}" y="${y}" ${extra}>${escapeHTML(value)}</text>`;
const title=value=>`<title>${escapeHTML(value)}</title>`;
const finite=value=>typeof value==='number'&&Number.isFinite(value);
function frame(view,body,height=290){return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 ${height}" role="img" aria-label="${escapeHTML(view.title)}"><style>text{font-family:inherit;fill:var(--muted);font-size:18px;stroke:none}.grid{stroke:var(--line);stroke-width:1}.label{fill:var(--fg);font-weight:650}.value{fill:var(--fg);font-size:12px;font-weight:700}</style>${title(view.title)}${body}</svg>`;}
function empty(){return '<div class="empty">Sin observaciones para esta selección.</div>';}
function legend(series){return `<div class="chart-legend">${series.map((s,i)=>`<span><i style="background:${s.color||palette[i%palette.length]}"></i>${escapeHTML(s.label||s.key)}</span>`).join('')}</div>`;}
function seriesOf(v){return v.series?.length?v.series:[{key:'value',label:v.unit||'Consultas',color:palette[0]}];}
function axes(min,max,unit,L=58,R=24,H=290,B=54){let g='';for(let i=0;i<=4;i++){let y=20+(H-B-20)*i/4;g+=`<line class="grid" x1="${L}" x2="${760-R}" y1="${y}" y2="${y}"/>`+text(L-9,y+4,formatValue(max-(max-min)*i/4,['%','percent','rate','porcentaje'].includes(unit)?unit:''),'text-anchor="end"');}return g;}
function cartesian(v){
  const rows=v.data||[],series=seriesOf(v);if(!rows.length)return empty();
  const L=62,R=v.type==='combo'?65:22,H=290,B=57,T=20,W=760-L-R;
  const left=series.filter(s=>s.axis!=='right'),right=series.filter(s=>s.axis==='right');
  const vals=rows.flatMap(r=>left.map(s=>r[s.key])).filter(finite);
  const stacks=v.type==='stacked'?rows.map(r=>left.reduce((n,s)=>n+(finite(r[s.key])?r[s.key]:0),0)):[];
  const min=Math.min(0,...vals),max=Math.max(1,...vals,...stacks),span=max-min||1;
  const rightMax=Math.max(1,...rows.flatMap(r=>right.map(s=>r[s.key])).filter(finite));
  const y=(value,s)=>H-B-(H-B-T)*(s?.axis==='right'?value/rightMax:(value-min)/span);
  let g=axes(min,max,v.unit||'',L,R,H,B);const bw=W/rows.length;
  if(right.length){for(let i=0;i<=4;i++)g+=text(760-R+9,T+(H-B-T)*i/4+4,formatValue(rightMax*(1-i/4),v.rightUnit||'%'));}
  if(v.type==='stacked')rows.forEach((r,i)=>{let base=0;series.forEach((s,j)=>{const value=r[s.key];if(!finite(value)||value<0)return;const top=y(base+value),bottom=y(base);g+=`<rect x="${L+i*bw+bw*.18}" y="${top}" width="${bw*.64}" height="${Math.max(0,bottom-top)}" fill="${s.color||palette[j%6]}">${title(`${r.label} · ${s.label}: ${formatValue(value,v.unit)}`)}</rect>`;base+=value;});});
  else series.forEach((s,j)=>{
    const isLine=['line','area'].includes(v.type)||(v.type==='combo'&&(s.axis==='right'||s.type==='line'));
    const points=rows.map((r,i)=>finite(r[s.key])?{x:L+bw*(i+.5),y:y(r[s.key],s),r}:null);
    if(isLine){
      let segment=[];const segments=[];for(const point of [...points,null]){if(point)segment.push(point);else if(segment.length){segments.push(segment);segment=[];}}
      for(const part of segments){const pts=part.map(p=>`${p.x},${p.y}`).join(' ');if(v.type==='area')g+=`<polygon points="${part[0].x},${y(0,s)} ${pts} ${part.at(-1).x},${y(0,s)}" fill="${s.color||palette[j%6]}" fill-opacity=".09"/>`;g+=`<polyline points="${pts}" fill="none" stroke="${s.color||palette[j%6]}" stroke-width="2.8" stroke-linejoin="round"/>`;}
      points.filter(Boolean).forEach(p=>g+=`<circle cx="${p.x}" cy="${p.y}" r="3.6" fill="${s.color||palette[j%6]}">${title(`${p.r.label} · ${s.label}: ${formatValue(p.r[s.key],s.axis==='right'?v.rightUnit||'%':v.unit)}`)}</circle>`);
    }else rows.forEach((r,i)=>{const value=r[s.key];if(!finite(value))return;const count=Math.max(1,left.length),width=bw*.68/count,x=L+i*bw+bw*.16+j*width,zero=y(0,s),yp=y(value,s);g+=`<rect x="${x}" y="${Math.min(yp,zero)}" width="${width*.91}" height="${Math.max(0,Math.abs(zero-yp))}" rx="2" fill="${s.color||palette[j%6]}">${title(`${r.label} · ${s.label}: ${formatValue(value,v.unit)}`)}</rect>`;});
  });
  rows.forEach((r,i)=>{const step=Math.max(1,Math.ceil(rows.length/8));if(i%step===0||(i===rows.length-1&&i%step>step/2))g+=text(L+bw*(i+.5),H-32,/^\d{4}-\d{2}-\d{2}$/.test(String(r.label))?String(r.label).slice(5):String(r.label).slice(0,16),'text-anchor="middle"');});
  return frame(v,g)+ (series.length>1?legend(series):'');
}
function horizontal(v){const rows=v.data||[];if(!rows.length)return empty();const height=Math.max(270,rows.length*33+45),L=260,R=85,max=Math.max(1,...rows.map(r=>r.value).filter(finite));let g='';rows.forEach((r,i)=>{const y=18+i*33,w=(760-L-R)*(r.value||0)/max;g+=text(L-12,y+13,String(r.label).slice(0,29),'text-anchor="end"')+`<rect x="${L}" y="${y}" width="${Math.max(0,w)}" height="20" rx="4" fill="${r.color||palette[i%6]}">${title(`${r.label}: ${formatValue(r.value,v.unit)}`)}</rect>`+text(L+w+8,y+14,formatValue(r.value,v.unit==='%'?'%':''),'class="label"');});return frame(v,g,height);}
function donut(v){const rows=(v.data||[]).filter(r=>finite(r.value)&&r.value>0),sum=rows.reduce((n,r)=>n+r.value,0);if(!sum)return empty();const cx=215,cy=140,r=94,C=2*Math.PI*r;let offset=0,g='';rows.forEach((row,i)=>{const length=row.value/sum*C;g+=`<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${row.color||palette[i%6]}" stroke-width="35" stroke-dasharray="${length} ${C-length}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})">${title(`${row.label}: ${formatValue(row.value,v.unit)} · ${formatValue(row.value/sum,'%')}`)}</circle>`;offset+=length;const yy=80+i*29;g+=`<rect x="390" y="${yy-10}" width="9" height="9" rx="3" fill="${row.color||palette[i%6]}"/>`+text(410,yy,String(row.label).slice(0,28))+text(710,yy,formatValue(row.value,v.unit),'class="label" text-anchor="end"');});g+=text(cx,cy,number.format(sum),'text-anchor="middle" style="font-size:34px;font-weight:750;fill:var(--fg)"')+text(cx,cy+23,'Total de consultas','text-anchor="middle" style="font-size:14px"');return frame(v,g);}
function funnel(v) {
  const rows=v.data||[],max=Math.max(0,...rows.map(r=>r.value));
  if(!max)return empty();
  const dark=['#1d4ed8','#6d28d9','#0e7490','#b45309'];
  let g='';
  rows.forEach((r,i)=>{
    const y=16+i*74,w=220+480*r.value/max;
    const next=i===rows.length-1?w*.85:220+480*rows[i+1].value/max;
    g+=`<path d="M${380-w/2},${y}h${w}L${380+next/2},${y+64}H${380-next/2}Z" fill="${dark[i%4]}">${title(`${r.label}: ${r.value} · ${formatValue(r.value/max,'%')}`)}</path>`;
    g+=text(380,y+28,r.label,'text-anchor="middle" style="fill:#fff;font-size:22px;font-weight:700"');
    g+=text(380,y+53,`${number.format(r.value)} · ${formatValue(r.value/max,'%')}`,'text-anchor="middle" style="fill:#fff;font-size:19px;font-weight:600"');
  });
  return frame(v,g,rows.length*74+24);
}
function heatmap(v){const {xLabels=[],yLabels=[],values=[]}=v.data||{};if(!values.length)return empty();const corr=v.type==='correlation',L=corr?175:75,R=15,T=35,cw=(760-L-R)/Math.max(1,xLabels.length),ch=corr?43:29,H=T+yLabels.length*ch+45,max=Math.max(1,...values.flat().filter(finite));let g='';xLabels.forEach((x,i)=>{if(!corr&&xLabels.length>12&&i%3!==0)return;g+=text(L+cw*(i+.5),T-10,String(x).slice(0,corr?11:8),'text-anchor="middle"');});values.forEach((row,i)=>{g+=text(L-10,T+ch*(i+.6),String(yLabels[i]).slice(0,corr?17:10),'text-anchor="end"');row.forEach((value,j)=>{const opacity=finite(value)?(corr?Math.abs(value):value/max)*.85+.08:.03;g+=`<rect x="${L+j*cw+1}" y="${T+i*ch+1}" width="${cw-3}" height="${ch-3}" rx="4" fill="${corr&&value<0?'#e05a76':'#2563eb'}" fill-opacity="${opacity}">${title(`${yLabels[i]} / ${xLabels[j]}: ${finite(value)?number.format(value):'Sin variación o sin pares'}${v.data.counts?` · n=${v.data.counts[i][j]}`:''}`)}</rect>`;if(corr)g+=text(L+cw*(j+.5),T+ch*(i+.63),finite(value)?value.toFixed(2):'—','text-anchor="middle" style="font-size:16px;fill:var(--fg);font-weight:700"');});});return frame(v,g,H)+(corr?'<p class="chart-note">Pearson · azul positivo, rosa negativo. Relación estadística, sin inferencia de causalidad. Consulta los pares en la tabla.</p>':'');}
function scatter(v){const rows=(v.data||[]).filter(r=>finite(r.x)&&finite(r.y));if(!rows.length)return empty();const L=60,R=24,T=20,H=290,B=53,xmin=Math.min(0,...rows.map(r=>r.x)),xmax=Math.max(1,...rows.map(r=>r.x)),ymin=Math.min(0,...rows.map(r=>r.y)),ymax=Math.max(1,...rows.map(r=>r.y));const x=a=>L+(760-L-R)*(a-xmin)/(xmax-xmin),y=a=>H-B-(H-B-T)*(a-ymin)/(ymax-ymin);let g=axes(ymin,ymax,v.yUnit||'',L,R,H,B);for(let i=0;i<=4;i++)g+=text(L+(760-L-R)*i/4,H-31,number.format(xmin+(xmax-xmin)*i/4),'text-anchor="middle"');if(v.reference==='diagonal')g+=`<line x1="${x(0)}" y1="${y(0)}" x2="${x(Math.min(xmax,ymax))}" y2="${y(Math.min(xmax,ymax))}" stroke="var(--muted)" stroke-dasharray="5 5"/>`;const groups=[...new Set(rows.map(r=>r.group))];rows.forEach(r=>g+=`<circle cx="${x(r.x)}" cy="${y(r.y)}" r="3.8" fill="${r.color||palette[Math.max(0,groups.indexOf(r.group))%6]}" fill-opacity=".58">${title(`${r.label||r.group||''} · ${v.xLabel||'X'}: ${r.x} · ${v.yLabel||'Y'}: ${r.y}`)}</circle>`);g+=text(400,H-4,v.xLabel||'','text-anchor="middle"')+text(13,140,v.yLabel||'','transform="rotate(-90 13 140)" text-anchor="middle"');return frame(v,g);}
function boxplot(v){const rows=(v.data||[]).filter(r=>['min','q1','median','q3','max'].every(key=>finite(r[key])));if(!rows.length)return empty();const L=155,R=30,max=Math.max(1,...rows.map(r=>r.max)),H=rows.length*57+50,x=a=>L+(760-L-R)*a/max;let g='';rows.forEach((r,i)=>{const y=30+i*57;g+=text(L-12,y+4,String(r.label).slice(0,16),'text-anchor="end"')+`<line x1="${x(r.min)}" x2="${x(r.max)}" y1="${y}" y2="${y}" stroke="#2563eb"/><line x1="${x(r.min)}" x2="${x(r.min)}" y1="${y-8}" y2="${y+8}" stroke="#2563eb"/><line x1="${x(r.max)}" x2="${x(r.max)}" y1="${y-8}" y2="${y+8}" stroke="#2563eb"/><rect x="${x(r.q1)}" y="${y-13}" width="${Math.max(1,x(r.q3)-x(r.q1))}" height="26" fill="var(--surface-2)" stroke="#2563eb" rx="3">${title(`${r.label}: mín ${r.min}, Q1 ${r.q1}, mediana ${r.median}, Q3 ${r.q3}, máx ${r.max} · n=${r.n}`)}</rect><line x1="${x(r.median)}" x2="${x(r.median)}" y1="${y-13}" y2="${y+13}" stroke="var(--fg)" stroke-width="3"/>`;});for(let i=0;i<=4;i++)g+=text(x(max*i/4),H-3,formatValue(max*i/4,v.unit),'text-anchor="middle"');return frame(v,g,H);}
export function renderChart(v){
  if(!v||!v.data)return empty();
  if(['bar','line','area','combo','stacked','histogram','pareto'].includes(v.type))return cartesian(v.type==='pareto'?{...v,type:'combo'}:v);
  if(v.type==='hbar')return horizontal(v);
  if(v.type==='donut')return donut(v);
  if(v.type==='funnel')return funnel(v);
  if(['heatmap','correlation'].includes(v.type))return heatmap(v);
  if(v.type==='scatter')return scatter(v);
  if(v.type==='boxplot')return boxplot(v);
  return empty();
}
export function tableForView(v){
  if(['heatmap','correlation'].includes(v.type)){const d=v.data;return {headers:['Fila',...d.xLabels],rows:d.yLabels.map((label,i)=>[label,...d.values[i].map((value,j)=>v.type==='correlation'?`${value==null?'—':number.format(value)} (n=${d.counts?.[i]?.[j]??'—'})`:formatValue(value))])};}
  const rows=v.data||[];if(v.type==='boxplot')return {headers:['Sistema','Mín.','Q1','Mediana','Q3','Máx.','n'],rows:rows.map(r=>[r.label,...['min','q1','median','q3','max','n'].map(k=>formatValue(r[k],k==='n'?'':v.unit))])};
  if(v.type==='scatter')return {headers:['Observación',v.xLabel||'X',v.yLabel||'Y'],rows:rows.map(r=>[r.label||r.group,formatValue(r.x,v.xUnit),formatValue(r.y,v.yUnit)])};
  const series=seriesOf(v);return {headers:['Categoría',...series.map(s=>s.label)],rows:rows.map(r=>[r.label,...series.map(s=>formatValue(r[s.key],s.axis==='right'?v.rightUnit||'%':v.unit))])};
}
