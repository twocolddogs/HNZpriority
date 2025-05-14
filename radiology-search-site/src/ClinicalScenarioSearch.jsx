import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const LogoUrl = "<HEALTH_NZ_LOGO_URL>";
const CTIconUrl = "/mnt/data/ct-scan.png";
const MRIIconUrl = "/mnt/data/mri-2.png";
const XrayIconUrl = "/mnt/data/x-rays.png";
const USIconUrl = "/mnt/data/ultrasound.png";

import data from "./dataset.json";

function getModalityIcon(modality) {
  if (/MR/i.test(modality)) return <><img src={MRIIconUrl} alt="MRI" className="w-5 h-5 inline mr-1" /> MRI</>;
  if (/CT/.test(modality)) return <><img src={CTIconUrl} alt="CT" className="w-5 h-5 inline mr-1" /> CT</>;
  if (/US/.test(modality)) return <><img src={USIconUrl} alt="Ultrasound" className="w-5 h-5 inline mr-1" /> Ultrasound</>;
  if (/(XR|DBI|X-ray)/i.test(modality)) return <><img src={XrayIconUrl} alt="X-ray" className="w-5 h-5 inline mr-1" /> X-ray</>;
  return <><Info className="w-5 h-5 inline mr-1 text-[#15284C]" /> {modality}</>;
}

export default function ClinicalScenarioSearch() {
  const [query, setQuery] = useState("");
  const grouped = data.reduce((acc, item) => {
    if (query.length < 3 || !item.scenario.toLowerCase().includes(query.toLowerCase())) return acc;
    acc[item.section] = acc[item.section] || {};
    acc[item.section][item.subheading || "General"] = acc[item.section][item.subheading || "General"] || [];
    acc[item.section][item.subheading || "General"].push(item);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-[#F6F4EC] p-4 md:p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <h1 className="w-full flex items-center justify-center text-3xl md:text-4xl font-bold text-[#15284C] mb-6">
          <img src={LogoUrl} alt="Health New Zealand" className="inline-block w-24 h-auto mr-3" />
          Health NZ Radiology Prioritisation Helper
        </h1>
        <Input
          placeholder="Search clinical scenarios..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full mb-8 border-2 border-[#15284C] rounded-md focus:ring-2 focus:ring-[#30A1AC]"
        />

        {query.length >= 3 && (
          Object.keys(grouped).length > 0 ? (
            Object.entries(grouped).map(([section, subgroups]) => (
              <div key={section} className="mb-8">
                <h2 className="text-2xl font-semibold text-[#15284C] mb-4">{section}</h2>
                {Object.entries(subgroups).map(([subheading, items]) => (
                  <div key={subheading} className="mb-6">
                    <h3 className="text-lg font-medium text-[#0C818F] mb-3">{subheading}</h3>
                    <div className="space-y-4">
                      {items.map((item, idx) => (
                        <Card key={idx} className="border-l-4 border-[#15284C] shadow rounded-lg">
                          <CardContent className="p-4 bg-white">
                            <div className="text-sm text-gray-600 uppercase tracking-wide mb-1">Clinical Scenario</div>
                            <div className="text-base text-gray-900 mb-3 whitespace-pre-wrap">{item.scenario}</div>
                            <div className="flex flex-wrap items-center gap-4 mb-3">
                              <span className="flex items-center bg-[#30A1AC] text-white px-3 py-1 rounded-full text-lg font-bold">{item.priority}</span>
                              <span className="flex items-center text-[#15284C] font-semibold">{getModalityIcon(item.modality)}</span>
                            </div>
                            <div className="text-sm text-gray-800"><span className="font-medium">Comments:&nbsp;</span>{item.comments || "None"}</div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))
          ) : (
            <p className="text-gray-600">No results found for "{query}".</p>
          )
        )}
      </div>
    </div>
  );
}
