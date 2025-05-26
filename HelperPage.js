// HelperPage.js
import React from "https://esm.sh/react";
const e = React.createElement;

export function HelperPage() {
  const createTableCellContent = (mainText, subText) => {
    return e(React.Fragment, null,
      mainText,
      subText && e('span', { className: 'rtt-table-cell-subtitle' }, subText)
    );
  };

  const createPriorityRow = (code, definition, overall, overallSub, reportWithin, reportWithinSub) => {
    // ... (normalization logic from before)
    let normalizedCodeForClass = code.toUpperCase();
    if (normalizedCodeForClass === "PET-CT") {
        normalizedCodeForClass = "petct";
    } else if (normalizedCodeForClass === "NA (OVERDUE REPORTING)") {
        normalizedCodeForClass = "na_overdue";
    } else {
        normalizedCodeForClass = normalizedCodeForClass.replace(/[^A-Z0-9]/g, '').toLowerCase();
    }
    const codeClassName = `rtt-helper-p-code rtt-helper-${normalizedCodeForClass}`;

    return e('tr', null,
      e('td', null, e('span', { className: codeClassName }, code)),
      e('td', null, definition),
      e('td', null, createTableCellContent(overall, overallSub)),
      e('td', null, createTableCellContent(reportWithin, reportWithinSub))
    );
  };

   const createAcutePriorityRow = (priority, definition, turnaround, turnaroundSub) => {
    return e('tr', null,
      e('td', null, priority), // This is "Patient Priority" in the Acute table
      e('td', null, definition),
      e('td', null, createTableCellContent(turnaround, turnaroundSub))
    );
  };

  return e('div', { className: 'rtt-helper-page-container' },
    // Radiology Patient Priority (P)
    e('details', { className: 'rtt-helper-collapsible-section', open: true },
      e('summary', null, e('h2', null, 'Radiology Patient Priority (P categories)')),
      e('div', { className: 'rtt-helper-collapsible-content' },
        e('div', { className: 'rtt-helper-table-responsive-wrapper' },
          e('table', null,
            e('thead', null,
              e('tr', null,
                e('th', { className: 'rtt-th-nowrap' }, 'Patient Priority'), // Applied nowrap
                e('th', null, 'Definition'),
                e('th', { className: 'rtt-th-nowrap' }, createTableCellContent('Overall Turnaround', '(Referral to Imaging)')), // Applied nowrap
                e('th', null, createTableCellContent('Report within', '(Imaging to Report Distribution)'))
              )
            ),
            // ... tbody for P categories
            e('tbody', null,
              createPriorityRow('P1', 'Non-deferrable time sensitive imaging or intervention that must be completed within 1 week of receiving referral.', '< 1 week', null, '24 hrs', null),
              createPriorityRow('P2', 'Non-deferrable imaging or intervention that must be completed within 2 weeks of receiving referral.', '< 2 weeks', null, '24 hrs', null),
              createPriorityRow('P3', 'Non-deferrable imaging or intervention that must be completed within 6* weeks of receiving referral.', '< 6* weeks', null, '48 hrs', null),
              createPriorityRow('P4', 'Deferrable. If capacity is constrained could wait up to 6-12* weeks from receiving referral.', '< 6* weeks', null, '48 hrs', null),
              createPriorityRow('P5', 'Deferrable low priority. If capacity is constrained could wait >12 weeks.', '< 6* weeks', null, '48 hrs', null),
              createPriorityRow('PET-CT', 'All PET-CT referrals except those with a specified future date.', '< 7 working days', null, 'N/A', null),
              createPriorityRow('NA (Overdue reporting)', 'Overdue reporting waiting > 24 or 48 hours outsourced to other services/providers.', 'NA', null, 'Up to 5 days by mutual agreement', null)
            )
          )
        ),
        e('div', { className: 'rtt-helper-note' },
          e('p', null, '*For community referred radiology the maximum reasonable wait is shorter - use 4 weeks instead of 6 weeks.')
        )
      )
    ),

    // Specified Date Patient Priority (S)
     e('details', { className: 'rtt-helper-collapsible-section' },
      e('summary', null, e('h2', null, 'Specified Date Patient Priority (S categories)')),
      e('div', { className: 'rtt-helper-collapsible-content' },
        e('div', { className: 'rtt-helper-table-responsive-wrapper' },
          e('table', null,
            e('thead', null,
              e('tr', null,
                e('th', { className: 'rtt-th-nowrap' }, 'Patient Priority'), // Applied nowrap
                e('th', null, 'Definition'),
                e('th', { className: 'rtt-th-nowrap' }, createTableCellContent('Overall Turnaround', '(to Imaging)')), // Applied nowrap
                e('th', null, createTableCellContent('Report within', '(Imaging to Report Distribution)'))
              )
            ),
            // ... tbody for S categories
             e('tbody', null,
              createPriorityRow('S1', 'Non-deferrable time sensitive imaging or intervention that must be completed within 1 week of a specified target date.', 'Within 1 week of specified target date', null, '24 hrs', null),
              createPriorityRow('S2', 'Non-deferrable time sensitive imaging or intervention that must be completed within 2 weeks of a specified target date.', 'Within 1 week of specified target date', null, '24 hrs', null),
              createPriorityRow('S3', 'Non-deferrable time sensitive imaging or intervention. If capacity is constrained could wait up to 6 weeks after a specified target date.', 'Within 1 week of specified target date', null, '48 hrs', null),
              createPriorityRow('S4', 'Deferrable time sensitive imaging or intervention. If capacity is constrained could wait up to 6-12 weeks after a specified target date.', 'Within 1 week of specified target date', null, '48 hrs', null),
              createPriorityRow('S5', 'Deferrable low priority imaging or intervention. If capacity is constrained could wait >12 weeks after a specified target date.', 'Within 1 week of specified target date', null, '48 hrs', null)
            )
          )
        ),
        // ... rest of S category content
        e('div', { className: 'rtt-helper-note' },
          e('p', null, 'Specified date imaging (S) refers to imaging that must be completed on a specific date or within a specified date range for clinical reasons based on a known diagnosis. Examples are protocols or guidelines that specify when imaging must occur to assess for treatment response or growth or progression of an incidental finding such as a pulmonary nodule.'),
          e('p', null, 'The S categories should not be used to drive meeting patient flow related targets such as FSA or MDM or clinic dates. Access to imaging and interventional services for any referrals not meeting the definition of specified date imaging should be based on the national by clinical indication recommended triage categories. These describe maximum reasonable waiting times based on the clinical indication/suspected diagnosis and associated risk.')
        ),
        e('h3', null, 'Detailed Explanation for S Categories'),
        e('div', { className: 'rtt-helper-explanation-content' }, 
          e('p', null, 'Specified date imaging (S) refers to imaging that must be completed on a specific date or within a specified date range for clinical reasons based on a known diagnosis.'),
          e('ul', null, e('li', null, 'Examples are Health Pathways or clinical protocols or guidelines that specify when imaging must occur to assess for treatment response or growth or progression of an incidental finding such as a pulmonary nodule.')),
          e('p', null, 'To avoid confusion with planned care terminology, as of 1 March 2023, the term specified date imaging will replace the term planned imaging Radiology services have historically used, including when reporting data for the CT and MRI indicators.'),
          e('ul', null, e('li', null, 'NRAG has updated the original guidance for planned imaging to reflect the new specified date terminology.')),
          e('p', null, 'The S categories should not be used to drive meeting patient flow related targets such as FSA or MDM or clinic dates.'),
          e('ul', null, e('li', null, 'Access to imaging and interventional services for any referrals not meeting the definition of specified date imaging should be based on the National Radiology Network by clinical indication recommended triage categories. These describe maximum reasonable waiting times based on the clinical indication/suspected diagnosis.')),
          e('p', null, 'Care needs to be taken if considering expediting some pathways of similar clinical priority over others to avoid unintended consequences for patients on other pathways.'),
          e('p', null, 'The goal of Radiology services should always be to have enough capacity to meet demand and to use fair, consistent triage criteria based on clinical indication to prioritise access.')
        )
      )
    ),
    
    // Acute Radiology Patient Priority
    e('details', { className: 'rtt-helper-collapsible-section' }, 
      e('summary', null, e('h2', null, 'Acute Radiology Patient Priority')),
      e('div', { className: 'rtt-helper-collapsible-content' },
        e('div', { className: 'rtt-helper-table-responsive-wrapper' },
          e('table', null,
            e('thead', null,
              e('tr', null,
                e('th', { className: 'rtt-th-nowrap' }, 'Patient Priority'), // Applied nowrap
                e('th', null, 'Definition'),
                e('th', null, createTableCellContent('Turnaround Time Target', '(Referral to Review or Report Distribution)'))
              )
            ),
            // ... tbody for Acute categories
             e('tbody', null,
              createAcutePriorityRow('< 30 minutes', 'Immediate life-threatening presentations. Image immediately.', '30 minutes*', null),
              createAcutePriorityRow('< 1 hr', 'All ED patients and inpatients that are clinically unwell. Ideally services should have capacity to image other ED and acute assessment patients in < 1 hr to support risk management, decision making and patient flow.', '1 hr*', null),
              createAcutePriorityRow('< 4 hrs', 'Most inpatient imaging. Imaging in < 4 hrs supports decision making and patient flow.', '4 hrs*', null),
              createAcutePriorityRow('< 24 hrs', 'Lower acuity inpatients and outpatients (including acute demand type primary care patients) that can wait up to 24 hrs.', '24 hrs', null),
              createAcutePriorityRow('< 2 days', 'Non-deferrable typically outpatient imaging that must be completed within 2 days.', '2 days', null)
            )
          )
        ),
        // ... rest of Acute category content
        e('div', { className: 'rtt-helper-note' },
          e('p', null, 'It is expected that the majority of ED imaging will be non-deferrable time sensitive imaging. In hospital settings, if ED and inpatient demand exceeds capacity, clinical triage across all patients waiting may trump any flow-based ED targets or priority pathways.'),
          e('p', null, '*Out of hours, emergency and inpatient imaging may receive a preliminary report or be reviewed by on-call medical staff, with final reports being completed in normal working hours.')
        )
      )
    ),
    // ... (Service Disruption, Reset and Restore, Planned Care sections remain the same)
    e('details', { className: 'rtt-helper-collapsible-section' },
      e('summary', null, e('h2', null, 'Service Disruption Levels')),
      e('div', { className: 'rtt-helper-collapsible-content' },
        e('ul', null,
          e('li', null, e('strong', null, 'Level 1 None:'), ' Managing baseline service delivery. All priorities 1-5 able to be imaged.'),
          e('li', null, e('strong', null, 'Level 2 Mild:'), ' Managing baseline service delivery but some staff shortage or equipment or facility issue is beginning to impact ability to maintain capacity and/or facility or equipment issue impacting capacity. Managing with modified ways of working that are not sustainable or are clinically undesirable such as extended hours of operation and/or overtime or additional shifts, providing more limited imaging or shifting staff or redirecting patients to other equipment/facility/service. Priorities 1-3 able to be imaged, some priority 4 may be imaged where capacity allows, imaging of priority 5 patients has paused.'),
          e('li', null, e('strong', null, 'Level 3 Moderate:'), ' Significant staff shortage with gaps not being covered or, significant reduction in capacity cf baseline due to equipment or facilities issue that cannot be resolved by available staff working extra or other modifications to the service. Outpatient/planned patient volumes moderately limited or if booked some need to be cancelled/rescheduled. Priorities 1-2 able to be imaged, some priority 3 may be imaged where capacity allows, imaging of priority 4 and 5 patients has paused.'),
          e('li', null, e('strong', null, 'Level 4 Severe:'), ' Critical staff shortage, gaps not being covered, and/or facility or equipment issue severely impacting capacity. Capacity limited to priority 1 mainly ED and inpatients, and few if any priority 2 or less urgent outpatients. Outpatient/planned patient volumes severely limited or if booked need to be cancelled/rescheduled.')
        ),
        e('h3', null, 'Impact of Service Disruption on P Priorities'),
        e('div', { className: 'rtt-helper-table-responsive-wrapper' },
          e('table', {className: 'rtt-helper-priority-impact-table'},
            e('thead', null, e('tr', null, e('th', null, 'Priority'), e('th', null, 'None'), e('th', null, 'Mild'), e('th', null, 'Moderate'), e('th', null, 'Severe'))),
            e('tbody', null,
              e('tr', null, e('td', null, 'P1'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes')),
              e('tr', null, e('td', null, 'P2'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'if-possible'}, 'If possible')),
              e('tr', null, e('td', null, 'P3'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'if-possible'}, 'If possible'), e('td', {className: 'x'}, 'x')),
              e('tr', null, e('td', null, 'P4'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'if-possible'}, 'If possible'), e('td', {className: 'x'}, 'x'), e('td', {className: 'x'}, 'x')),
              e('tr', null, e('td', null, 'P5'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'x'}, 'x'), e('td', {className: 'x'}, 'x'), e('td', {className: 'x'}, 'x'))
            )
          )
        ),
        e('h3', null, 'Impact of Service Disruption on S Priorities'),
        e('div', { className: 'rtt-helper-table-responsive-wrapper' },
          e('table', {className: 'rtt-helper-priority-impact-table'},
            e('thead', null, e('tr', null, e('th', null, 'Priority'), e('th', null, 'None'), e('th', null, 'Mild'), e('th', null, 'Moderate'), e('th', null, 'Severe'))),
            e('tbody', null,
              e('tr', null, e('td', null, 'S1'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes')),
              e('tr', null, e('td', null, 'S2'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'if-possible'}, 'If possible')),
              e('tr', null, e('td', null, 'S3'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'if-possible'}, 'If possible'), e('td', {className: 'x'}, 'x')),
              e('tr', null, e('td', null, 'S4'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'if-possible'}, 'If possible'), e('td', {className: 'x'}, 'x'), e('td', {className: 'x'}, 'x')),
              e('tr', null, e('td', null, 'S5'), e('td', {className: 'yes'}, 'Yes'), e('td', {className: 'x'}, 'x'), e('td', {className: 'x'}, 'x'), e('td', {className: 'x'}, 'x'))
            )
          )
        )
      )
    ),

    // Reset and Restore
    e('details', { className: 'rtt-helper-collapsible-section' },
      e('summary', null, e('h2', null, 'Reset and Restore')),
      e('div', { className: 'rtt-helper-collapsible-content' },
        e('ul', null,
          e('li', null, 'If delay/cessation of any services are required: Services for Māori and other at-risk populations must be the last to be stopped in any priority band.'),
          e('li', null, 'When restarting services that have been deferred: Services for Māori and other at-risk populations should be the first services restarted in each priority band.')
        )
      )
    ),

    // Planned Care Task Force Recommendations
    e('details', { className: 'rtt-helper-collapsible-section' },
      e('summary', null, e('h2', null, 'Planned Care Task Force Recommendations')),
      e('div', { className: 'rtt-helper-collapsible-content' },
        e('h3', null, 'Prioritisation guidance P1-5'),
        e('ul', null,
          e('li', null, 'Reset and restore 45: Ensure Nationally consistent prioritisation systems'),
          e('li', null, 'Reset and restore 46: Mandate each region to establish consistency of approach to radiology waiting list management'),
          e('li', null, 'Enabler: Regionally/nationally consistent waiting list reporting')
        ),
        e('h3', null, 'Specified date guidance S1-5'),
        e('ul', null, e('li', null, 'Reset and restore 45: Ensure Nationally consistent prioritisation systems')),
        e('h3', null, 'Service disruption level guidance'),
        e('ul', null,
          e('li', null, 'Reset and restore 3: Confirm an explicit prioritisation framework if delay/cessation of any services are required'),
          e('li', null, 'Reset and restore 4: Confirm an explicit prioritisation framework for restarting services that have been deferred')
        )
      )
    )
  );
}
