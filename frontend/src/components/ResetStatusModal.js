import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { useState } from "react";

const ResetStatusModal = ({ 
  open, 
  onClose, 
  onConfirm, 
  selectedCount, 
  currentCategory 
}) => {
  const [scope, setScope] = useState("all");

  const handleConfirm = () => {
    onConfirm(scope);
    onClose();
  };

  return (
    <AlertDialog open={open} onOpenChange={onClose}>
      <AlertDialogContent className="bg-[#2C2C2E] border-[#3A3A3C] text-[#EAEAEA]">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-xl font-bold gradient-text">
            Reset Status Confirmation
          </AlertDialogTitle>
          <AlertDialogDescription className="text-gray-400 mt-2">
            Choose which contacts to reset. This will:
            <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
              <li>Set status to PENDING (⏳)</li>
              <li>Clear sent timestamps and messages</li>
              <li>Reset classification and interest scores</li>
              <li>Update counters and progress bars</li>
            </ul>
          </AlertDialogDescription>
        </AlertDialogHeader>

        <RadioGroup
          value={scope}
          onValueChange={setScope}
          className="space-y-3 mt-4"
        >
          <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-[#3A3A3C] transition-colors">
            <RadioGroupItem
              value="all"
              id="all"
              data-testid="reset-scope-all"
              className="border-gray-500"
            />
            <Label htmlFor="all" className="flex-1 cursor-pointer">
              <div className="font-medium">All Categories</div>
              <div className="text-sm text-gray-400">
                Reset every contact across all categories
              </div>
            </Label>
          </div>

          {currentCategory && (
            <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-[#3A3A3C] transition-colors">
              <RadioGroupItem
                value="category"
                id="category"
                data-testid="reset-scope-category"
                className="border-gray-500"
              />
              <Label htmlFor="category" className="flex-1 cursor-pointer">
                <div className="font-medium">Current Category Only</div>
                <div className="text-sm text-gray-400">
                  Reset contacts in "{currentCategory.name}" category
                </div>
              </Label>
            </div>
          )}

          {selectedCount > 0 && (
            <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-[#3A3A3C] transition-colors">
              <RadioGroupItem
                value="selected"
                id="selected"
                data-testid="reset-scope-selected"
                className="border-gray-500"
              />
              <Label htmlFor="selected" className="flex-1 cursor-pointer">
                <div className="font-medium">Selected Contacts Only</div>
                <div className="text-sm text-gray-400">
                  Reset {selectedCount} selected contact(s)
                </div>
              </Label>
            </div>
          )}
        </RadioGroup>

        <AlertDialogFooter className="mt-6">
          <AlertDialogCancel
            data-testid="reset-cancel-btn"
            className="bg-[#3A3A3C] hover:bg-[#48484A] border-0 text-white"
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            data-testid="reset-confirm-btn"
            className="gradient-accent text-white hover:opacity-90"
          >
            Reset Status
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default ResetStatusModal;
