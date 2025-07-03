import React, { useState } from 'react';
import { ChevronRight, RotateCcw, FileText, AlertCircle, Info, BookOpen, ArrowLeft } from 'lucide-react';

const LiverImagingTool = () => {
  const [currentStep, setCurrentStep] = useState('start');
  const [stepHistory, setStepHistory] = useState(['start']);
  const [answers, setAnswers] = useState({});
  const [recommendation, setRecommendation] = useState(null);
  const [showProtocols, setShowProtocols] = useState(false);

  const resetTool = () => {
    setCurrentStep('start');
    setStepHistory(['start']);
    setAnswers({});
    setRecommendation(null);
  };

  const goBack = () => {
    if (stepHistory.length > 1) {
      const newHistory = [...stepHistory];
      newHistory.pop(); // Remove current step
      const previousStep = newHistory[newHistory.length - 1];
      setStepHistory(newHistory);
      setCurrentStep(previousStep);
      setRecommendation(null);
    }
  };

  const handleAnswer = (step, answer, nextStep, rec = null) => {
    setAnswers({...answers, [step]: answer});
    if (rec) {
      setRecommendation(rec);
      setCurrentStep('result');
      setStepHistory([...stepHistory, 'result']);
    } else {
      setCurrentStep(nextStep);
      setStepHistory([...stepHistory, nextStep]);
    }
  };

  const StepCard = ({ children, title }) => (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">{title}</h2>
      {children}
    </div>
  );

  const Button = ({ onClick, children, variant = 'primary', className = '' }) => {
    const baseClasses = "px-6 py-3 rounded-lg font-medium transition-colors duration-200 flex items-center gap-2";
    const variants = {
      primary: "bg-white hover:bg-blue-600 text-gray-800 hover:text-white border-2 border-blue-600 transition-all duration-200",
      secondary: "bg-gray-200 hover:bg-gray-300 text-gray-800 border-2 border-gray-300 transition-all duration-200",
      success: "bg-white hover:bg-green-600 text-gray-800 hover:text-white border-2 border-green-600 transition-all duration-200",
      warning: "bg-white hover:bg-orange-500 text-gray-800 hover:text-white border-2 border-orange-500 transition-all duration-200",
      info: "bg-indigo-500 hover:bg-indigo-600 text-white border-2 border-indigo-500 transition-all duration-200"
    };
    
    return (
      <button 
        onClick={onClick}
        className={`${baseClasses} ${variants[variant]} ${className}`}
      >
        {children}
      </button>
    );
  };

  const BackButton = () => (
    stepHistory.length > 1 && (
      <Button 
        onClick={goBack} 
        variant="secondary" 
        className="inline-flex"
      >
        <ArrowLeft size={16} />
        Back
      </Button>
    )
  );

  const RecommendationCard = ({ rec }) => (
    <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-6">
      <div className="flex items-start gap-3">
        <FileText className="text-green-600 mt-1" size={24} />
        <div>
          <h3 className="font-semibold text-green-800 text-lg mb-2">Recommended Imaging</h3>
          <div className="space-y-2">
            <p className="text-gray-800"><strong>Modality:</strong> {rec.modality}</p>
            <p className="text-gray-800"><strong>Contrast:</strong> {rec.contrast}</p>
          </div>
        </div>
      </div>
    </div>
  );

  const ProtocolReference = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-bold text-gray-800">Protocol Reference Guide</h3>
            <button 
              onClick={() => setShowProtocols(false)}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>
          
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-800 mb-2">Pancreatic Protocol CT</h4>
              <p className="text-blue-700">Early arterial phase upper abdomen + portal venous phase abdomen and pelvis</p>
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <h4 className="font-semibold text-purple-800 mb-3">TYPE OF MRI CONTRAST</h4>
              
              <div className="space-y-3">
                <div className="bg-white p-3 rounded border">
                  <h5 className="font-semibold text-purple-700 mb-2">Primovist</h5>
                  <ul className="text-sm text-gray-700 space-y-1">
                    <li>• If there is evidence of malignancy on prior imaging</li>
                    <li>• Solid/complex liver lesion</li>
                    <li>• Gallbladder lesions ?malignancy</li>
                    <li>• Pancreatic malignancy including high risk or large/enlarging IPMNs</li>
                  </ul>
                </div>

                <div className="bg-white p-3 rounded border">
                  <h5 className="font-semibold text-purple-700 mb-2">Other patients can have Dotarem or Gadovist</h5>
                  <p className="text-sm text-gray-700 mb-2">Examples:</p>
                  <ul className="text-sm text-gray-700 space-y-1">
                    <li>• Question of haemangioma with no other malignancy or solid liver lesion</li>
                    <li>• Routine low risk IPMN follow up</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  if (currentStep === 'start') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Liver Imaging Decision Support Tool</h1>
            <p className="text-gray-600">Interactive guide for selecting appropriate imaging modality and contrast</p>
          </div>

          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>
          
          <StepCard title="Patient Presentation">
            <div className="space-y-4">
              <p className="text-gray-700">What is the primary clinical scenario?</p>
              <div className="grid gap-3">
                <Button 
                  onClick={() => handleAnswer('start', 'cirrhosis-risk', 'result', {
                    modality: 'MRI liver',
                    contrast: 'with Gadovist (in line with Auckland unless specified by MDM)',
                    notes: 'Direct pathway for cirrhosis/risk factors with no other malignancy suspected'
                  })}
                  className="justify-start text-left"
                >
                  <AlertCircle size={20} />
                  Cirrhosis or risk factors for cirrhosis and no other malignancy suspected. Outside CT or US showing liver lesion
                </Button>
                <Button 
                  onClick={() => handleAnswer('start', 'under-40', 'under-40-branch')}
                  variant="secondary"
                  className="justify-start text-left"
                >
                  <ChevronRight size={20} />
                  Patients less than 40 years old
                </Button>
                <Button 
                  onClick={() => handleAnswer('start', 'over-40', 'over-40-branch')}
                  variant="secondary"
                  className="justify-start text-left"
                >
                  <ChevronRight size={20} />
                  Patients greater than 40 years old
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'under-40-branch') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="Patients Less Than 40 Years Old">
            <div className="space-y-4">
              <p className="text-gray-700">What was found on initial imaging?</p>
              <div className="grid gap-3">
                <Button 
                  onClick={() => handleAnswer('under-40-branch', 'incidental-liver', 'under-40-ct-pancreas')}
                  className="justify-start text-left"
                >
                  Incidentally detected liver lesions on ultrasound
                </Button>
                <Button 
                  onClick={() => handleAnswer('under-40-branch', 'symptoms-lft', 'under-40-symptoms-decision')}
                  variant="secondary"
                  className="justify-start text-left"
                >
                  Symptoms or abnormal LFTs and ultrasound/CT confirms gallstones
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'under-40-ct-pancreas') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="CT Pancreatic Mass Protocol">
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <h4 className="font-semibold text-blue-800 mb-2">CT Pancreatic Mass Protocol</h4>
                <p className="text-blue-700">Early arterial phase upper abdomen + portal venous phase abdomen and pelvis</p>
                <div className="mt-2 p-2 bg-yellow-100 border-l-4 border-yellow-400 rounded">
                  <p className="text-sm text-yellow-800"><strong>Note:</strong> MRI preferred, but CT undertaken first due to MRI resource constraints</p>
                </div>
              </div>
              
              <p className="text-gray-700 font-medium">Has the CT already been completed?</p>
              <div className="flex gap-4 justify-center">
                <Button 
                  onClick={() => handleAnswer('under-40-ct-pancreas', 'yes', 'under-40-characterization')}
                  variant="success"
                >
                  Yes
                </Button>
                <Button 
                  onClick={() => handleAnswer('under-40-ct-pancreas', 'no', 'result', {
                    modality: 'CT Pancreatic Mass Protocol',
                    contrast: 'Early arterial phase upper abdomen + portal venous phase abdomen and pelvis',
                    notes: ''
                  })}
                  variant="warning"
                >
                  No
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'under-40-characterization') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="Pancreatic CT Completed">
            <div className="space-y-4">
              <p className="text-gray-700 font-medium">Is further characterisation or assessment required?</p>
              <div className="flex justify-center">
                <Button 
                  onClick={() => handleAnswer('under-40-characterization', 'yes', 'result', {
                    modality: 'MRCP/MRI liver/pancreas',
                    contrast: 'with Gadolinium (see protocol reference for contrast selection)',
                    notes: ''
                  })}
                  variant="success"
                >
                  Yes
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'under-40-symptoms-decision') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="Patient < 40 symptoms or proven gallstones">
            <div className="space-y-4">
              <p className="text-gray-700 font-medium">?CBD stone is the only question</p>
              <div className="flex gap-4 justify-center">
                <Button 
                  onClick={() => handleAnswer('under-40-symptoms-decision', 'yes', 'result', {
                    modality: 'MRCP',
                    contrast: '(CT not required)',
                    notes: ''
                  })}
                  variant="success"
                >
                  Yes
                </Button>
                <Button 
                  onClick={() => handleAnswer('under-40-symptoms-decision', 'no', 'under-40-ct-check')}
                  variant="warning"
                >
                  No
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'under-40-ct-check') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="CT Pancreatic Mass Protocol">
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <h4 className="font-semibold text-blue-800 mb-2">CT Pancreatic Mass Protocol</h4>
                <p className="text-blue-700">Early arterial phase upper abdomen + portal venous phase abdomen and pelvis</p>
              </div>
              
              <p className="text-gray-700 font-medium">Has the CT already been completed and there is still diagnostic uncertainty?</p>
              <div className="flex justify-center">
                <Button 
                  onClick={() => handleAnswer('under-40-ct-check', 'yes', 'result', {
                    modality: 'MRCP/MRI liver/pancreas',
                    contrast: 'with Gadolinium (see protocol reference for contrast selection)',
                    notes: ''
                  })}
                  variant="success"
                >
                  Yes
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'under-40-mrcp-decision') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="CBD Stone Assessment">
            <div className="space-y-4">
              <p className="text-gray-700">For symptoms/abnormal LFTs with confirmed gallstones:</p>
              <Button 
                onClick={() => handleAnswer('under-40-mrcp-decision', 'mrcp', 'result', {
                  modality: 'MRCP',
                  contrast: '(CT not required)',
                  notes: ''
                })}
                variant="success"
                className="w-full justify-center"
              >
                <FileText size={20} />
                Proceed with MRCP
              </Button>
              <Button onClick={resetTool} variant="secondary" className="mt-4">
                <RotateCcw size={16} />
                Start Over
              </Button>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'over-40-branch') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="Patients Greater Than 40 Years Old">
            <div className="space-y-4">
              <p className="text-gray-700">What clinical scenario applies?</p>
              <div className="grid gap-3">
                <Button 
                  onClick={() => handleAnswer('over-40-branch', 'new-lesions', 'over-40-ct-pancreas')}
                  className="justify-start text-left"
                >
                  Incidentally detected new/concerning liver lesions on ultrasound
                </Button>
                <Button 
                  onClick={() => handleAnswer('over-40-branch', 'abdominal-lft', 'over-40-ct-pancreas')}
                  variant="secondary"
                  className="justify-start text-left"
                >
                  Abdominal ultrasound for abnormal LFTs. Question is ?gallstone or pancreaticobiliary pathology
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'over-40-ct-pancreas') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="CT Pancreatic Mass Protocol">
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <h4 className="font-semibold text-blue-800 mb-2">CT Pancreatic Mass Protocol</h4>
                <p className="text-blue-700">Early arterial phase upper abdomen + portal venous phase abdomen and pelvis</p>
              </div>
              
              <p className="text-gray-700 font-medium">Has the CT already been completed?</p>
              <div className="flex gap-4 justify-center">
                <Button 
                  onClick={() => handleAnswer('over-40-ct-pancreas', 'yes', 'over-40-characterization')}
                  variant="success"
                >
                  Yes
                </Button>
                <Button 
                  onClick={() => handleAnswer('over-40-ct-pancreas', 'no', 'result', {
                    modality: 'CT Pancreatic Mass Protocol',
                    contrast: 'Early arterial phase upper abdomen + portal venous phase abdomen and pelvis',
                    notes: ''
                  })}
                  variant="warning"
                >
                  No
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'over-40-characterization') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>

          <StepCard title="Pancreatic CT Completed">
            <div className="space-y-4">
              <p className="text-gray-700 font-medium">Is further characterisation or assessment required?</p>
              <div className="flex justify-center">
                <Button 
                  onClick={() => handleAnswer('over-40-characterization', 'yes', 'result', {
                    modality: 'MRCP/MRI liver/pancreas',
                    contrast: 'with Gadolinium (see protocol reference for contrast selection)',
                    notes: ''
                  })}
                  variant="success"
                >
                  Yes
                </Button>
              </div>
              <div className="flex gap-2 mt-4">
                <BackButton />
                <Button onClick={resetTool} variant="secondary">
                  <RotateCcw size={16} />
                  Start Over
                </Button>
              </div>
            </div>
          </StepCard>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  if (currentStep === 'result') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-100 p-4">
        <div className="max-w-4xl mx-auto py-8">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-800 mb-2">Imaging Recommendation</h1>
          </div>

          <div className="mb-6 text-center">
            <Button 
              onClick={() => setShowProtocols(true)}
              variant="info"
              className="inline-flex"
            >
              <BookOpen size={16} />
              View Protocol Reference Guide
            </Button>
          </div>
          
          <RecommendationCard rec={recommendation} />
          
          <div className="mt-8 flex justify-center gap-4">
            <BackButton />
            <Button onClick={resetTool} variant="primary">
              <RotateCcw size={16} />
              Start New Assessment
            </Button>
          </div>
        </div>
        {showProtocols && <ProtocolReference />}
      </div>
    );
  }

  return null;
};

export default LiverImagingTool;