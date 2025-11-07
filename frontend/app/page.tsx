import MainLayout from '@/components/MainLayout';
import LeftSidebar from '@/components/LeftSidebar';
import CenterChat from '@/components/CenterChat';
import RightSidebar from '@/components/RightSidebar';

export default function Home() {
  return (
    <MainLayout>
      <div className="flex h-[calc(100vh-73px)]">
        <LeftSidebar />
        <CenterChat />
        <RightSidebar />
      </div>
    </MainLayout>
  );
}
