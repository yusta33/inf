import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { PlusCircle, Upload, Users, Send } from 'lucide-react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}/api`;

function DashboardPage() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAddingContact, setIsAddingContact] = useState(false);
  const [newContact, setNewContact] = useState({
    username: '',
    platform: 'email',
    categoryName: '',
  });

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/categories`);
      setCategories(response.data);
    } catch (error) {
      toast.error('Failed to fetch categories');
    } finally {
      setLoading(false);
    }
  };

  const handleAddContact = async () => {
    if (!newContact.username || !newContact.categoryName) {
      toast.error('Please fill in all fields');
      return;
    }

    try {
      // Find or create category
      let category = categories.find(c => c.name === newContact.categoryName);
      let categoryId;

      if (!category) {
        // Create new category
        categoryId = `cat-${Date.now()}`;
        const newCategory = {
          id: categoryId,
          name: newContact.categoryName,
          total_contacts: 0,
          sent_count: 0,
        };

        // We'll create it via the contact creation since there's no separate category endpoint
        // For now, just use the ID
      } else {
        categoryId = category.id;
      }

      // Create contact manually via direct DB insert simulation
      // Since there's no direct create contact endpoint, we'd need to use excel import
      // For now, let's show a toast that this would require backend update
      toast.info('Contact creation requires Excel import. Use the Upload button.');
      setIsAddingContact(false);

    } catch (error) {
      toast.error('Failed to add contact');
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/excel/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      toast.success(`Imported ${response.data.total_contacts} contacts`);
      fetchCategories();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import contacts');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-[#EAEAEA]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-[#EAEAEA]">Dashboard</h1>
          <p className="text-[#8E8E93] mt-1">Manage your contacts and campaigns</p>
        </div>

        <div className="flex gap-3">
          <label htmlFor="file-upload">
            <Button asChild variant="outline" className="cursor-pointer">
              <span>
                <Upload className="mr-2 h-4 w-4" />
                Import Excel
              </span>
            </Button>
          </label>
          <input
            id="file-upload"
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileUpload}
            className="hidden"
          />

          <Dialog open={isAddingContact} onOpenChange={setIsAddingContact}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700">
                <PlusCircle className="mr-2 h-4 w-4" />
                Add Contact
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#2C2C2E] text-[#EAEAEA] border-[#48484A]">
              <DialogHeader>
                <DialogTitle>Add New Contact</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label>Username / Email</Label>
                  <Input
                    value={newContact.username}
                    onChange={(e) => setNewContact({ ...newContact, username: e.target.value })}
                    placeholder="contact@example.com or @username"
                    className="bg-[#3C3C3E] border-[#48484A]"
                  />
                </div>

                <div>
                  <Label>Platform</Label>
                  <Select
                    value={newContact.platform}
                    onValueChange={(value) => setNewContact({ ...newContact, platform: value })}
                  >
                    <SelectTrigger className="bg-[#3C3C3E] border-[#48484A]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#2C2C2E] border-[#48484A]">
                      <SelectItem value="email">Email</SelectItem>
                      <SelectItem value="instagram">Instagram</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Category</Label>
                  <Input
                    value={newContact.categoryName}
                    onChange={(e) => setNewContact({ ...newContact, categoryName: e.target.value })}
                    placeholder="e.g., Influencers, Customers"
                    className="bg-[#3C3C3E] border-[#48484A]"
                  />
                </div>

                <Button onClick={handleAddContact} className="w-full bg-blue-600 hover:bg-blue-700">
                  Add Contact
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-[#2C2C2E] border-[#48484A]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[#8E8E93]">Total Contacts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#EAEAEA]">
              {categories.reduce((sum, cat) => sum + cat.total_contacts, 0)}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#2C2C2E] border-[#48484A]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[#8E8E93]">Messages Sent</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#EAEAEA]">
              {categories.reduce((sum, cat) => sum + cat.sent_count, 0)}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#2C2C2E] border-[#48484A]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[#8E8E93]">Categories</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#EAEAEA]">{categories.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Categories and Contacts */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-[#EAEAEA]">Categories & Contacts</h2>

        {categories.length === 0 ? (
          <Card className="bg-[#2C2C2E] border-[#48484A]">
            <CardContent className="py-12 text-center">
              <Users className="mx-auto h-12 w-12 text-[#8E8E93] mb-4" />
              <h3 className="text-lg font-medium text-[#EAEAEA] mb-2">No contacts yet</h3>
              <p className="text-[#8E8E93] mb-4">
                Import an Excel file or add contacts manually to get started
              </p>
            </CardContent>
          </Card>
        ) : (
          categories.map((category) => (
            <Card key={category.id} className="bg-[#2C2C2E] border-[#48484A]">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle className="text-[#EAEAEA]">{category.name}</CardTitle>
                  <div className="flex gap-2">
                    <Badge variant="secondary" className="bg-[#3C3C3E] text-[#EAEAEA]">
                      {category.total_contacts} contacts
                    </Badge>
                    <Badge variant="secondary" className="bg-blue-600/20 text-blue-400">
                      {category.sent_count} sent
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {category.contacts && category.contacts.slice(0, 5).map((contact) => (
                    <div
                      key={contact.id}
                      className="flex justify-between items-center p-3 bg-[#3C3C3E] rounded-lg"
                    >
                      <div>
                        <div className="text-[#EAEAEA] font-medium">{contact.username}</div>
                        <div className="text-[#8E8E93] text-sm">{contact.platform}</div>
                      </div>
                      <Badge
                        variant={
                          contact.status === 'sent'
                            ? 'default'
                            : contact.status === 'failed'
                            ? 'destructive'
                            : 'secondary'
                        }
                        className={
                          contact.status === 'sent'
                            ? 'bg-green-600'
                            : contact.status === 'failed'
                            ? 'bg-red-600'
                            : 'bg-[#48484A]'
                        }
                      >
                        {contact.status}
                      </Badge>
                    </div>
                  ))}
                  {category.contacts && category.contacts.length > 5 && (
                    <div className="text-center text-[#8E8E93] text-sm pt-2">
                      +{category.contacts.length - 5} more contacts
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

export default DashboardPage;
