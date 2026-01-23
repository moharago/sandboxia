## counseling

- 0
  ```json
  {
    "applicant": {
      "companyName": "",
      "department": "",
      "position": "",
      "name": "",
      "businessAddress": "",
      "phoneNumber": "",
      "email": "",
      "consultationDate": ""
    },
    "technologyService": {
      "serviceName": "",
      "description": {
        "purposeAndNecessity": "",
        "technologyOverview": "",
        "innovationAndDifferentiation": ""
      }
    },
    "consultation": {
      "regulationInquiry": "",
      "relatedLaws": "",
      "referenceMaterials": ""
    }
  }
  ```

## fastcheck

- 1-1
  ```json
  {
    "receipt": {
      "receiptNumber": "",
      "receiptDate": ""
    },
    "applicant": {
      "companyName": "",
      "businessRegistrationNumber": "",
      "address": "",
      "representativeName": "",
      "phoneNumber": "",
      "email": ""
    },
    "technologyService": {
      "name": "",
      "type": {
        "technology": false,
        "service": false,
        "technologyAndService": false
      },
      "mainContent": ""
    },
    "authority": {
      "expectedGoverningAgency": "",
      "expectedPermitOrApproval": ""
    },
    "application": {
      "applicationDate": "",
      "applicantSignature": ""
    },
    "attachments": {
      "technologyServiceDescriptionIncluded": false
    }
  }
  ```
- 1-2
  ```json
  {
    "technologyServiceDetails": {
      "title": "",
      "description": "",
      "serviceFlow": "",
      "coreTechnologies": "",
      "architectureDiagram": ""
    },
    "legalIssues": {
      "relatedRegulations": "",
      "questionsByAuthority": [
        {
          "lawOrRegulation": "",
          "authority": "",
          "question": ""
        }
      ]
    },
    "additionalQuestions": {
      "content": ""
    }
  }
  ```

## temporary

- 2-1
  ```json
  {
    "receipt": {
      "receiptNumber": "",
      "receiptDate": ""
    },
    "applicant": {
      "companyName": "",
      "businessRegistrationNumber": "",
      "address": "",
      "representativeName": "",
      "phoneNumber": "",
      "email": ""
    },
    "technologyService": {
      "name": "",
      "type": {
        "technology": false,
        "service": false,
        "technologyAndService": false
      },
      "mainContent": ""
    },
    "temporaryPermitReason": {
      "noApplicableStandards": false,
      "unclearOrUnreasonableStandards": false
    },
    "application": {
      "applicationDate": "",
      "applicantSignature": ""
    },
    "attachments": {
      "businessPlanIncluded": false,
      "article37ExplanationIncluded": false,
      "safetyVerificationAndUserProtectionPlanIncluded": false,
      "additionalRequestedMaterialsIncluded": false
    }
  }
  ```
- 2-2
  ```json
  {
    "projectInfo": {
      "projectName": "",
      "period": {
        "startDate": "",
        "endDate": "",
        "durationMonths": ""
      }
    },
    "applicantOrganizations": [
      {
        "organizationName": "",
        "organizationType": "",
        "responsiblePersonName": "",
        "position": "",
        "phoneNumber": "",
        "email": ""
      }
    ],
    "technologyService": {
      "detailedDescription": {
        "title": "",
        "content": "",
        "serviceFlow": "",
        "coreTechnologies": "",
        "architectureDiagram": "",
        "differentiation": {
          "domesticOrSimilarExistence": "",
          "improvementOverExisting": ""
        }
      },
      "marketStatusAndOutlook": {
        "domesticStatus": "",
        "globalStatus": "",
        "marketSize": {
          "domestic": "",
          "global": "",
          "evidenceSources": ""
        }
      }
    },
    "temporaryPermitRequest": {
      "regulationDetails": {
        "legalSystemOverview": "",
        "targetRegulationContent": ""
      },
      "necessityAndRequest": {
        "necessity": "",
        "requestedPermitDetails": ""
      }
    },
    "businessPlan": {
      "objectivesAndScope": {
        "objectives": "",
        "targetScope": "",
        "justification": ""
      },
      "businessContent": {
        "detailedDescription": "",
        "systemAndProcessDiagram": "",
        "serviceFlow": "",
        "coreTechnologies": "",
        "personalDataProtectionPlan": ""
      },
      "schedule": {
        "overallPeriod": "",
        "milestones": ""
      }
    },
    "operationPlan": {
      "environmentAndUsers": "",
      "monitoringAndControl": "",
      "performanceMeasurement": "",
      "reportingPlan": ""
    },
    "expectedEffects": {
      "quantitative": {
        "economic": "",
        "social": "",
        "userBenefits": "",
        "evidence": ""
      },
      "qualitative": {
        "economic": "",
        "userConvenience": ""
      }
    },
    "expansionPlan": {
      "roadmap": "",
      "investmentAndHiring": "",
      "expectedEffects": ""
    },
    "organizationAndBudget": {
      "organizationStructure": {
        "management": "",
        "userProtection": "",
        "rolesAndResponsibilities": ""
      },
      "budget": {
        "annualOperationCost": "",
        "insuranceOrUserProtectionCost": ""
      }
    },
    "attachments": {
      "organizationStatusDocumentIncluded": false,
      "organizationSealCertificateIncluded": false
    },
    "submission": {
      "submissionDate": "",
      "signatures": [
        {
          "organizationName": "",
          "name": "",
          "signature": ""
        }
      ]
    }
  }
  ```
- 2-5
  ```json
  {
    "temporaryPermitReason": {
      "eligibility": {
        "noApplicableStandards": false,
        "unclearOrUnreasonableStandards": false
      },
      "justification": ""
    }
  }
  ```
- 2-6
  ```json
  {
    "safetyAndUserProtection": {
      "safetyVerification": {
        "verificationMethod": "",
        "evidenceAndBasis": "",
        "results": "",
        "externalTesting": {
          "performed": false,
          "testingOrganization": "",
          "details": "",
          "attachments": []
        },
        "partialOrUnavailableTesting": {
          "reason": "",
          "opinionDocument": ""
        }
      },
      "userProtectionPlan": {
        "protectionScope": {
          "financial": "",
          "physical": "",
          "lifeAndSafety": "",
          "personalData": ""
        },
        "temporaryPermitNotificationMethod": "",
        "damagePreventionAndResponse": {
          "prevention": "",
          "response": "",
          "damageMinimization": "",
          "damageRelief": ""
        },
        "compensationMeasures": {
          "liabilityInsurance": false,
          "damageInsurance": false,
          "otherMeasures": ""
        },
        "complaintHandlingProcess": ""
      },
      "riskAndResponse": {
        "riskScenarios": [
          {
            "riskCategory": "",
            "scenarioDescription": "",
            "responsePlan": ""
          }
        ],
        "damageItemsAndCompensationPlan": ""
      },
      "stakeholderConflictResolution": {
        "potentialConflicts": "",
        "fairnessAndRightsImpact": "",
        "mitigationMeasures": "",
        "consultationPlan": ""
      }
    }
  }
  ```

## demonstration

- 3-1
  ```json
  {
    "receipt": {
      "receiptNumber": "",
      "receiptDate": ""
    },
    "applicant": {
      "companyName": "",
      "businessRegistrationNumber": "",
      "address": "",
      "representativeName": "",
      "phoneNumber": "",
      "email": ""
    },
    "technologyService": {
      "name": "",
      "type": {
        "technology": false,
        "service": false,
        "technologyAndService": false
      },
      "mainContent": ""
    },
    "regulatoryExemptionReason": {
      "reason1_impossibleToApplyPermit": false,
      "reason2_unclearOrUnreasonableCriteria": false
    },
    "application": {
      "applicationDate": "",
      "applicantSignature": ""
    },
    "attachments": {
      "testPlanIncluded": false,
      "article38ExplanationIncluded": false,
      "userProtectionPlanIncluded": false,
      "additionalRequestedMaterialsIncluded": false
    }
  }
  ```
- 3-2

  ```json
  {
    "testProject": {
      "name": "",
      "period": {
        "startDate": "",
        "endDate": "",
        "durationMonths": ""
      }
    },
    "applicantOrganizations": [
      {
        "organizationName": "",
        "organizationType": "",
        "responsiblePersonName": "",
        "position": "",
        "phoneNumber": "",
        "email": ""
      }
    ],
    "submission": {
      "submissionDate": "",
      "confirmCompliance": true
    },
    "attachments": {
      "organizationStatusDocumentIncluded": false,
      "organizationSealCertificateIncluded": false
    },
    "signatures": [
      {
        "organizationName": "",
        "name": "",
        "signature": ""
      }
    ],

    "technologyService": {
      "detailedDescription": {
        "title": "",
        "content": "",
        "serviceFlow": "",
        "coreTechnologies": "",
        "architectureDiagram": "",
        "differentiation": {
          "domesticOrSimilarExistence": "",
          "improvementOverExisting": ""
        }
      },
      "marketStatusAndOutlook": {
        "domesticStatus": "",
        "globalStatus": "",
        "marketSize": {
          "domestic": "",
          "global": "",
          "evidenceSources": ""
        }
      }
    },
    "regulatoryExemption": {
      "regulationDetails": {
        "legalSystemOverview": "",
        "targetRegulationContent": ""
      },
      "necessityAndRequest": {
        "necessity": "",
        "requestedExemptionDetails": ""
      }
    },
    "testPlan": {
      "objectivesAndScope": {
        "objectives": "",
        "necessity": "",
        "targetScope": ""
      },
      "executionMethod": {
        "stages": "",
        "detailedScenario": "",
        "personalDataProtectionPlan": ""
      },
      "schedule": {
        "overallPeriod": "",
        "milestones": ""
      }
    },
    "operationPlan": {
      "environmentAndUsers": "",
      "monitoringAndControl": "",
      "performanceMeasurement": "",
      "reportingPlan": ""
    },
    "expectedEffects": {
      "quantitative": {
        "economic": "",
        "social": "",
        "userBenefits": "",
        "evidence": ""
      },
      "qualitative": {
        "economic": "",
        "userConvenience": ""
      }
    },
    "postTestPlan": {
      "expansionPlan": {
        "businessExpansion": "",
        "roadmap": "",
        "investmentAndHiring": "",
        "expectedEffects": ""
      },
      "restorationPlan": {
        "originalStateRecovery": ""
      }
    },
    "organizationAndBudget": {
      "organizationStructure": {
        "management": "",
        "userProtection": "",
        "rolesAndResponsibilities": ""
      },
      "budget": {
        "annualOperationCost": "",
        "insuranceOrUserProtectionCost": ""
      }
    },
    "applicantOrganizationProfile": {
      "generalInfo": {
        "organizationName": "",
        "establishmentDate": "",
        "representativeName": "",
        "address": ""
      },
      "businessOverview": "",
      "licenses": "",
      "technologiesAndPatents": "",
      "financialStatus": {
        "totalAssets": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "equity": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "currentLiabilities": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "fixedLiabilities": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "currentAssets": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "operatingIncome": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "revenue": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "returnOnEquity": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        },
        "debtRatio": {
          "yearM2": "",
          "yearM1": "",
          "average": ""
        }
      },
      "organizationChart": "",
      "humanResources": {
        "totalEmployees": "",
        "keyPersonnel": [
          {
            "name": "",
            "department": "",
            "position": "",
            "responsibility": "",
            "skillsOrCertifications": "",
            "experienceYears": ""
          }
        ]
      },
      "attachments": {
        "businessRegistrationCopyIncluded": false,
        "financialStatementIncluded": false,
        "creditRatingReportIncluded": false
      }
    }
  }
  ```

- 3-5
  ```json
  {
    "regulatoryExemptionReason": {
      "eligibility": {
        "impossibleToApplyPermitByOtherLaw": false,
        "unclearOrUnreasonableCriteria": false
      },
      "justification": ""
    }
  }
  ```
- 3-6
  ```json
  {
    "userProtectionPlan": {
      "protectionAndResponse": {
        "protectionMeasures": {
          "financial": "",
          "physical": "",
          "lifeAndSafety": "",
          "personalData": ""
        },
        "userNotificationMethod": "",
        "damageResponsePlan": {
          "recovery": "",
          "response": "",
          "damageMinimization": "",
          "damageRelief": ""
        },
        "compensationPlan": {
          "liabilityInsurance": false,
          "damageInsurance": false,
          "otherMeasures": ""
        },
        "complaintHandlingProcess": ""
      },
      "riskAndMitigation": {
        "riskScenarios": [
          {
            "riskType": "",
            "description": "",
            "mitigationPlan": ""
          }
        ],
        "damageItemsAndCompensation": ""
      },
      "stakeholderConflict": {
        "potentialConflicts": "",
        "impactAnalysis": "",
        "resolutionPlan": "",
        "consultationOrAgreementPlan": ""
      }
    }
  }
  ```
