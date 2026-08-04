import Carousel from "../components/Carousel/Carousel";

export default function Home({ showLoginInitially = false }) {
  return (
    <div className="home-page">
      <Carousel initialShowLogin={showLoginInitially} />
    </div>
  );
}
