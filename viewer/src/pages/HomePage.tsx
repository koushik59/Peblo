import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCatalog, Show, Section } from '../api';
import ShowDetailModal from '../components/ShowDetailModal';
import HeroCarousel from '../components/HeroCarousel';
import SectionRow from '../components/SectionRow';

export default function HomePage() {
  const [selectedShow, setSelectedShow] = useState<Show | null>(null);

  const { data: catalog, isLoading, error } = useQuery({
    queryKey: ['catalog'],
    queryFn: getCatalog,
  });

  if (isLoading) {
    return (
      <div className="loading-spinner">
        <div className="spinner-circle" />
        <div>Loading entertainment...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state" style={{ paddingTop: '150px' }}>
        <h3>Could not load catalogue</h3>
        <p>The catalogue service may still be publishing. Please check back shortly.</p>
      </div>
    );
  }

  const sections: Section[] = catalog?.sections || [];
  const allShows: Show[] = sections.flatMap((sec) => sec.shows);

  // Top featured shows for the hero showcase (deduplicated)
  const uniqueFeaturedShows: Show[] = Array.from(
    new Map(allShows.map((s) => [s.id, s])).values()
  );

  const formatSectionTitle = (name: string) => {
    switch (name.toLowerCase()) {
      case 'featured':
        return 'Featured & Trending Shows';
      case 'series':
        return 'Popular Series & Drama';
      case 'minisodes':
        return 'Top Quick Minisodes';
      case 'songs':
        return 'Singalong Hits & Music';
      default:
        return name.charAt(0).toUpperCase() + name.slice(1);
    }
  };

  return (
    <div className="home-page-container">
      {/* JioHotstar Signature Hero Showcase */}
      {uniqueFeaturedShows.length > 0 && (
        <HeroCarousel
          shows={uniqueFeaturedShows}
          onSelectShow={setSelectedShow}
          isModalOpen={!!selectedShow}
        />
      )}

      {/* Content Rows */}
      <div className="sections-wrapper">
        {sections.length === 0 ? (
          <div className="empty-state">
            <h3>No Published Content</h3>
            <p>The catalogue has not been published yet. Log in to the CMS to publish shows.</p>
          </div>
        ) : (
          sections.map((section) => (
            <SectionRow
              key={section.name}
              title={formatSectionTitle(section.name)}
              shows={section.shows}
              onSelectShow={setSelectedShow}
            />
          ))
        )}
      </div>

      {/* Show Detail Modal */}
      {selectedShow && (
        <ShowDetailModal show={selectedShow} onClose={() => setSelectedShow(null)} />
      )}
    </div>
  );
}
